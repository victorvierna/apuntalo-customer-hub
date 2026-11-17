"""Instagram reader: reads the inbox of one account and fills the inbound queue.

It only reads and queues (``docs/architecture/gateway.md``, section 2). It does
not decide anything and does not write ``contacts``, ``conversations`` or
``messages``: that is the gateway's job.

Every pass re-reads the most recent conversations. Messages that are already in
the queue are not queued again (``UNIQUE``), so a re-read never looks like a new
message and the reader does not need to remember where it stopped.

**Bursts.** Contacts often write one query in several messages. When a read
finds new messages from the contact, the reader reads that conversation again
``QUIET_PERIOD`` later, and again while it keeps finding new ones. The gateway
waits for a re-read that finds nothing new, so it answers the whole burst once
(``shared/db/queue.py``). Due re-reads go before the next conversation of the
pass, so they do not wait for the pass to end. Between passes, call
``run_due_rechecks`` often.

**History (``is_backfill``).** Everything is queued and stored, so the assistant
has the whole conversation as context. What history means is "do not answer it
as if it had just arrived" (decided on 2026-11-17):

- The first pass of an account is all history: we never answer the past.
- A conversation the reader has never seen (instagram-cli only returns the 10
  most recent, so older ones show up when someone writes again): what came
  before our last reply was already answered, so it is history; what the
  contact wrote after it is answered. A message request accepted in the app has
  no reply of ours, so all of it is answered.
- A conversation we already know: everything new is answered.

How often the reader runs, and how it is started, is still open
(``gateway.md``, open decision 1).
"""

import logging
import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from shared.db.connection import to_db_time, transaction
from shared.db.queue import (
    due_rechecks,
    enqueue,
    has_synced,
    is_known_conversation,
    last_known_message_id,
    last_queued_conversation,
    mark_checked,
    postpone_recheck,
)
from shared.types.messages import ChannelConversation, ChannelMessage, Direction

from .adapter import INBOX_MAX, InstagramAdapter
from .errors import InstagramAuthError, InstagramCliError, InstagramCliNotFoundError

logger = logging.getLogger(__name__)

CONVERSATIONS_LIMIT = 20
"""Asked for in every pass. instagram-cli 2.1.0 returns at most 10 anyway."""

MESSAGES_LIMIT = 20
"""Messages per ``read`` page."""

MAX_PAGES = 10
"""Pages read back in one conversation looking for the last message we already have.

With 20 messages a page, this is 200 messages of margin. If the anchor is still not
found, the conversation is reported as a gap instead of reading forever.
"""

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class PollResult:
    """What the reader did, for logs and the dashboard."""

    first_sync: bool = False
    conversations_read: int = 0
    rechecks: int = 0
    """Re-reads of conversations with a burst going on."""

    messages_queued: int = 0
    groups_skipped: int = 0
    failed_conversations: list[str] = field(default_factory=list)
    """Conversations that could not be read this pass. The next pass retries them."""
    gap_conversations: list[str] = field(default_factory=list)
    """Conversations where the last message we had is not in the pages read, so
    some messages may have been lost (more than ``MAX_PAGES`` pages came in while
    the reader was down). A person should look at them."""
    inbox_full: bool = False
    """``inbox`` returned as many conversations as it can. Older conversations may
    be missing from this pass; they show up again when someone writes."""


def poll_once(
    conn: sqlite3.Connection,
    adapter: InstagramAdapter,
    channel_account_id: int,
    clock: Clock = _utc_now,
) -> PollResult:
    """One pass over the recent conversations of one account, plus due re-reads.

    ``adapter`` must be logged in to the account of ``channel_account_id``.
    ``clock`` gives the current time; only tests change it.

    Raises:
        InstagramAuthError: the session expired; a person has to log in again.
        InstagramCliNotFoundError: instagram-cli is not installed.
        InstagramCliError: the inbox itself could not be read.
    """
    # Decided once, before queuing anything: after the first conversation of
    # the first pass, the account would already look synced.
    result = PollResult(first_sync=not has_synced(conn, channel_account_id))

    conversations = adapter.list_conversations(limit=CONVERSATIONS_LIMIT)
    if len(conversations) >= INBOX_MAX:
        result.inbox_full = True
        logger.warning(
            "Inbox of account %s returned %d conversations (the maximum); older ones may be missing.",
            channel_account_id,
            len(conversations),
        )

    for conversation in conversations:
        run_due_rechecks(conn, adapter, channel_account_id, clock, result)
        # Group conversations are not in the MVP.
        if len(conversation.participants) > 1:
            result.groups_skipped += 1
            continue
        known = not result.first_sync and is_known_conversation(
            conn, channel_account_id, conversation.external_id
        )
        _read_and_queue(
            conn, adapter, channel_account_id, conversation, clock, result,
            first_sync=result.first_sync, known=known,
        )

    run_due_rechecks(conn, adapter, channel_account_id, clock, result)
    return result


def run_due_rechecks(
    conn: sqlite3.Connection,
    adapter: InstagramAdapter,
    channel_account_id: int,
    clock: Clock = _utc_now,
    result: PollResult | None = None,
) -> PollResult:
    """Re-reads the conversations of an account whose re-read is due.

    Raises the same errors as ``poll_once`` for an expired session or a
    missing instagram-cli; any other failure postpones that re-read.
    """
    result = result if result is not None else PollResult()
    for conversation_id in due_rechecks(conn, channel_account_id, to_db_time(clock())):
        conversation = last_queued_conversation(conn, channel_account_id, conversation_id)
        if conversation is None:
            # Its queue rows were cleaned up: nothing to wait for any more.
            with transaction(conn):
                mark_checked(conn, channel_account_id, conversation_id, to_db_time(clock()), False)
            continue
        result.rechecks += 1
        _read_and_queue(
            conn, adapter, channel_account_id, conversation, clock, result,
            first_sync=False, known=True,
        )
    return result


def _read_and_queue(
    conn: sqlite3.Connection,
    adapter: InstagramAdapter,
    channel_account_id: int,
    conversation: ChannelConversation,
    clock: Clock,
    result: PollResult,
    *,
    first_sync: bool,
    known: bool,
) -> None:
    """Reads one conversation back to its anchor and queues what is new, with its check,
    in one transaction."""
    # The start of the read: everything sent before it is in what we read.
    read_at = to_db_time(clock())
    anchor = (
        last_known_message_id(conn, channel_account_id, conversation.external_id)
        if known
        else None
    )
    try:
        messages, has_older = _read_back_to(adapter, conversation.external_id, anchor)
    except (InstagramAuthError, InstagramCliNotFoundError):
        raise
    except InstagramCliError:
        # One conversation failing does not stop the others.
        logger.exception(
            "Could not read conversation %s of account %s",
            conversation.external_id,
            channel_account_id,
        )
        result.failed_conversations.append(conversation.external_id)
        with transaction(conn):
            postpone_recheck(conn, channel_account_id, conversation.external_id, read_at)
        return

    if anchor is not None and has_older and not any(m.external_id == anchor for m in messages):
        result.gap_conversations.append(conversation.external_id)
        logger.warning(
            "Conversation %s of account %s: the last message we had is not in the %d pages read; messages may be lost.",
            conversation.external_id,
            channel_account_id,
            MAX_PAGES,
        )

    flags = backfill_flags(messages, first_sync=first_sync, known=known)
    found_new_incoming = False
    with transaction(conn):
        for message, is_backfill in zip(messages, flags, strict=True):
            if enqueue(conn, channel_account_id, conversation, message, read_at, is_backfill):
                result.messages_queued += 1
                if not is_backfill and message.direction is Direction.IN:
                    found_new_incoming = True
        mark_checked(conn, channel_account_id, conversation.external_id, read_at, found_new_incoming)
    result.conversations_read += 1


def _read_back_to(
    adapter: InstagramAdapter, conversation_id: str, anchor: str | None
) -> tuple[list[ChannelMessage], bool]:
    """The newest messages of a conversation, oldest first, going back to ``anchor``.

    Reads pages until the anchor (the last message we already have) shows up, there
    are no older messages, or ``MAX_PAGES`` pages were read. Returns the messages and
    whether older messages still exist that were not read.
    """
    page = adapter.read_page(conversation_id, limit=MESSAGES_LIMIT)
    messages = list(page.messages)
    cursor = page.next_cursor
    pages = 1
    while (
        anchor is not None
        and cursor is not None
        and not any(m.external_id == anchor for m in messages)
        and pages < MAX_PAGES
    ):
        page = adapter.read_page(conversation_id, limit=MESSAGES_LIMIT, cursor=cursor)
        messages = page.messages + messages
        cursor = page.next_cursor
        pages += 1
    return messages, cursor is not None


def backfill_flags(
    messages: Sequence[ChannelMessage], *, first_sync: bool, known: bool
) -> list[bool]:
    """Which messages are history (``True``), in the same order as ``messages``.

    See the module documentation for the rules.
    """
    if first_sync:
        return [True] * len(messages)
    if known:
        return [False] * len(messages)
    replies = [m.created_at for m in messages if m.direction is Direction.OUT]
    if not replies:
        return [False] * len(messages)
    last_reply = max(replies)
    return [m.created_at <= last_reply for m in messages]

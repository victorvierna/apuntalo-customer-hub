"""Instagram reader: reads the inbox of one account and fills the inbound queue.

It only reads and queues (``docs/architecture/gateway.md``, section 2). It does
not decide anything and does not write ``contacts``, ``conversations`` or
``messages``: that is the gateway's job.

Every pass re-reads the most recent conversations. Messages that are already in
the queue are not queued again (``UNIQUE``), so a re-read never looks like a new
message and the reader does not need to remember where it stopped.

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

How often ``poll_once`` runs, and how it is started, is still open
(``gateway.md``, open decision 1).
"""

import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from shared.db.connection import to_db_time, transaction
from shared.db.queue import enqueue, has_synced, is_known_conversation
from shared.types.messages import ChannelMessage, Direction

from .adapter import InstagramAdapter
from .errors import InstagramAuthError, InstagramCliError, InstagramCliNotFoundError

logger = logging.getLogger(__name__)

CONVERSATIONS_LIMIT = 20
"""Asked for in every pass. instagram-cli 2.1.0 returns at most 10 anyway."""

MESSAGES_LIMIT = 20
"""Latest messages read from each conversation."""


@dataclass(slots=True)
class PollResult:
    """What one pass did, for logs and the dashboard."""

    first_sync: bool
    conversations_read: int = 0
    messages_queued: int = 0
    groups_skipped: int = 0
    failed_conversations: list[str] = field(default_factory=list)
    """Conversations that could not be read this pass. The next pass retries them."""


def poll_once(
    conn: sqlite3.Connection,
    adapter: InstagramAdapter,
    channel_account_id: int,
    now: datetime | None = None,
) -> PollResult:
    """Reads the recent conversations of one account and queues their messages.

    ``adapter`` must be logged in to the account of ``channel_account_id``.

    Each conversation is queued in its own transaction, so the gateway never
    sees half of what was read from it.

    Raises:
        InstagramAuthError: the session expired; a person has to log in again.
        InstagramCliNotFoundError: instagram-cli is not installed.
        InstagramCliError: the inbox itself could not be read.
    """
    now_text = to_db_time(now or datetime.now(UTC))
    # Decided once, before queuing anything: after the first conversation of
    # the first pass, the account would already look synced.
    result = PollResult(first_sync=not has_synced(conn, channel_account_id))

    for conversation in adapter.list_conversations(limit=CONVERSATIONS_LIMIT):
        # Group conversations are not in the MVP.
        if len(conversation.participants) > 1:
            result.groups_skipped += 1
            continue
        try:
            messages = adapter.read_messages(conversation.external_id, limit=MESSAGES_LIMIT)
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
            continue

        known = not result.first_sync and is_known_conversation(
            conn, channel_account_id, conversation.external_id
        )
        flags = backfill_flags(messages, first_sync=result.first_sync, known=known)
        with transaction(conn):
            for message, is_backfill in zip(messages, flags, strict=True):
                if enqueue(conn, channel_account_id, conversation, message, now_text, is_backfill):
                    result.messages_queued += 1
        result.conversations_read += 1

    return result


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

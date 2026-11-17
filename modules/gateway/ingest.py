"""Steps 1 to 4 of the gateway: store a burst (``gateway.md`` section 4).

Identity, conversation and messages, without duplicates. Nothing here decides
whether the assistant answers: that is ``checks.py``.
"""

import sqlite3
from dataclasses import dataclass

from shared.db.connection import to_db_time
from shared.db.conversations import (
    create_conversation,
    find_conversation,
    insert_message,
    touch_conversation,
)
from shared.types.messages import ChannelMessage, Direction
from shared.types.queue import QueuedMessage

from .identity import Identity, resolve_identity

# Notes saved in inbound_queue.error for rows skipped on purpose.
SKIP_GROUP = "skipped: group conversation (not in the MVP)"
SKIP_UNKNOWN_CONTACT = (
    "skipped: outgoing message in a conversation with a person who is not in the "
    "database yet (not in the MVP)"
)


@dataclass(frozen=True, slots=True)
class StoredBurst:
    conversation_id: int
    conversation_status: str
    identity: Identity | None
    """None when the burst only had outgoing messages."""

    fresh: tuple[tuple[int, ChannelMessage], ...]
    """New incoming messages that are not history: ``(message_id, message)``,
    oldest first. Only these can be answered."""


def store_burst(
    conn: sqlite3.Connection, burst: list[QueuedMessage], now: str
) -> StoredBurst | str:
    """Stores the messages of a burst. Returns a skip note if it cannot be stored.

    All messages of a burst are from the same conversation.
    """
    account_id = burst[0].channel_account_id
    # The latest read has the most up-to-date participants and title.
    conversation = burst[-1].conversation
    if len(conversation.participants) > 1:
        return SKIP_GROUP

    # Only an incoming message tells us who the other person is: in an outgoing
    # one the sender is our own account.
    incoming = [item for item in burst if item.message.direction is Direction.IN]
    identity = None
    if incoming:
        identity = resolve_identity(
            conn,
            channel=conversation.channel,
            external_id=incoming[-1].message.sender_external_id,
            username=conversation.participants[0] if conversation.participants else None,
            display_name=conversation.title or None,
            now=now,
        )

    messages = sorted(burst, key=lambda item: item.message.created_at)
    last_message_at = to_db_time(messages[-1].message.created_at)

    row = find_conversation(conn, account_id, conversation.external_id)
    if row is None:
        if identity is None:
            return SKIP_UNKNOWN_CONTACT
        conversation_id = create_conversation(
            conn, account_id, identity.contact_id, conversation.external_id, last_message_at, now
        )
        status = "bot"
    else:
        conversation_id, status = row["id"], row["status"]
        touch_conversation(conn, conversation_id, last_message_at)

    fresh = []
    for item in messages:
        message_id = insert_message(conn, conversation_id, item.message)
        # None = already stored (a re-read, or a row queued again after a cleanup).
        if message_id is not None and item.message.direction is Direction.IN and not item.is_backfill:
            fresh.append((message_id, item.message))

    return StoredBurst(conversation_id, status, identity, tuple(fresh))

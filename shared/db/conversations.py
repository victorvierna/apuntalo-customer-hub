"""Conversations, messages and handoffs (``database.md`` 6.3, 6.4 and 6.9)."""

import sqlite3

from shared.db.connection import to_db_time
from shared.types.messages import ChannelMessage, Direction


def find_conversation(
    conn: sqlite3.Connection, channel_account_id: int, external_id: str
) -> sqlite3.Row | None:
    """``id``, ``contact_id`` and ``status`` of a channel conversation, if we have it."""
    return conn.execute(
        """
        SELECT id, contact_id, status FROM conversations
        WHERE channel_account_id = ? AND external_id = ?
        """,
        (channel_account_id, external_id),
    ).fetchone()


def create_conversation(
    conn: sqlite3.Connection,
    channel_account_id: int,
    contact_id: int,
    external_id: str,
    last_message_at: str,
    now: str,
) -> int:
    return conn.execute(
        """
        INSERT INTO conversations (channel_account_id, contact_id, external_id,
                                   last_message_at, created_at)
        VALUES (?, ?, ?, ?, ?)
        RETURNING id
        """,
        (channel_account_id, contact_id, external_id, last_message_at, now),
    ).fetchone()["id"]


def touch_conversation(conn: sqlite3.Connection, conversation_id: int, last_message_at: str) -> None:
    """Moves ``last_message_at`` forward (never back: old messages can arrive late)."""
    conn.execute(
        "UPDATE conversations SET last_message_at = MAX(last_message_at, ?) WHERE id = ?",
        (last_message_at, conversation_id),
    )


def set_conversation_status(conn: sqlite3.Connection, conversation_id: int, status: str) -> None:
    conn.execute("UPDATE conversations SET status = ? WHERE id = ?", (status, conversation_id))


def insert_message(
    conn: sqlite3.Connection, conversation_id: int, message: ChannelMessage
) -> int | None:
    """Stores a message read from the channel. Returns None if it was already stored.

    An outgoing message read from the channel that we do not have was not sent
    by the assistant (it stores what it sends), so a person wrote it from the
    channel's own app.
    """
    incoming = message.direction is Direction.IN
    row = conn.execute(
        """
        INSERT INTO messages (conversation_id, direction, author, content_type, body,
                              external_id, delivery_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (conversation_id, external_id) DO NOTHING
        RETURNING id
        """,
        (
            conversation_id,
            message.direction.value,
            "contact" if incoming else "human",
            message.content_type.value,
            message.body,
            message.external_id,
            None if incoming else "sent",
            to_db_time(message.created_at),
        ),
    ).fetchone()
    return row["id"] if row else None


def create_handoff(
    conn: sqlite3.Connection, conversation_id: int, run_id: int, reason: str, now: str
) -> int:
    return conn.execute(
        """
        INSERT INTO handoffs (conversation_id, run_id, reason, created_at)
        VALUES (?, ?, ?, ?)
        RETURNING id
        """,
        (conversation_id, run_id, reason, now),
    ).fetchone()["id"]

"""The inbound queue (``inbound_queue``, ``database.md`` 6.14).

Channel readers write with ``enqueue()``. The gateway reads whole bursts and
marks them done in the same transaction in which it stores the messages.
"""

import sqlite3

from shared.types.messages import ChannelConversation, ChannelMessage
from shared.types.queue import QueuedMessage, decode_payload, encode_payload


def enqueue(
    conn: sqlite3.Connection,
    channel_account_id: int,
    conversation: ChannelConversation,
    message: ChannelMessage,
    now: str,
    is_backfill: bool = False,
) -> bool:
    """Adds a message read from the channel. Returns False if it was already queued.

    Readers re-read recent conversations on every pass; re-reads insert
    nothing, so they never look like new messages.
    """
    row = conn.execute(
        """
        INSERT INTO inbound_queue (channel_account_id, conversation_external_id,
                                   message_external_id, is_backfill, payload, enqueued_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (channel_account_id, message_external_id) DO NOTHING
        RETURNING id
        """,
        (
            channel_account_id,
            conversation.external_id,
            message.external_id,
            int(is_backfill),
            encode_payload(conversation, message),
            now,
        ),
    ).fetchone()
    return row is not None


def ready_conversations(conn: sqlite3.Connection, quiet_since: str) -> list[tuple[int, str]]:
    """Conversations with pending messages and no new message after ``quiet_since``.

    Returns ``(channel_account_id, conversation_external_id)`` pairs, the
    oldest burst first.
    """
    rows = conn.execute(
        """
        SELECT channel_account_id, conversation_external_id
        FROM inbound_queue
        WHERE status = 'pending'
        GROUP BY channel_account_id, conversation_external_id
        HAVING MAX(enqueued_at) <= ?
        ORDER BY MIN(enqueued_at)
        """,
        (quiet_since,),
    ).fetchall()
    return [(row["channel_account_id"], row["conversation_external_id"]) for row in rows]


def pending_burst(
    conn: sqlite3.Connection, channel_account_id: int, conversation_external_id: str
) -> list[QueuedMessage]:
    """All pending messages of a conversation, in the order they were queued."""
    rows = conn.execute(
        """
        SELECT id, channel_account_id, is_backfill, payload
        FROM inbound_queue
        WHERE status = 'pending' AND channel_account_id = ? AND conversation_external_id = ?
        ORDER BY id
        """,
        (channel_account_id, conversation_external_id),
    ).fetchall()
    burst = []
    for row in rows:
        conversation, message = decode_payload(row["payload"])
        burst.append(
            QueuedMessage(
                queue_id=row["id"],
                channel_account_id=row["channel_account_id"],
                is_backfill=bool(row["is_backfill"]),
                conversation=conversation,
                message=message,
            )
        )
    return burst


def mark_done(
    conn: sqlite3.Connection, queue_ids: list[int], now: str, note: str | None = None
) -> None:
    """Marks rows as done. ``note`` explains rows skipped on purpose (saved in ``error``)."""
    conn.executemany(
        """
        UPDATE inbound_queue
        SET status = 'done', started_at = ?, finished_at = ?, error = ?
        WHERE id = ?
        """,
        [(now, now, note, queue_id) for queue_id in queue_ids],
    )


def record_failure(
    conn: sqlite3.Connection,
    channel_account_id: int,
    conversation_external_id: str,
    error: str,
    now: str,
    max_attempts: int,
) -> None:
    """Counts a failed attempt on the pending rows of a conversation.

    They stay ``pending`` to be retried, until ``max_attempts``: then they
    become ``failed`` and the dashboard shows them.
    """
    conn.execute(
        """
        UPDATE inbound_queue
        SET attempts = attempts + 1,
            error = ?,
            status = CASE WHEN attempts + 1 >= ? THEN 'failed' ELSE 'pending' END,
            started_at = CASE WHEN attempts + 1 >= ? THEN ? ELSE started_at END,
            finished_at = CASE WHEN attempts + 1 >= ? THEN ? ELSE finished_at END
        WHERE status = 'pending' AND channel_account_id = ? AND conversation_external_id = ?
        """,
        (
            error,
            max_attempts,
            max_attempts,
            now,
            max_attempts,
            now,
            channel_account_id,
            conversation_external_id,
        ),
    )


def has_synced(conn: sqlite3.Connection, channel_account_id: int) -> bool:
    """Whether the reader already read this account at least once.

    Also looks at ``conversations``: old ``done`` rows of the queue can be
    deleted (``database.md``, open decision 13), but stored conversations stay.
    """
    row = conn.execute(
        """
        SELECT EXISTS (SELECT 1 FROM inbound_queue WHERE channel_account_id = ?)
            OR EXISTS (SELECT 1 FROM conversations WHERE channel_account_id = ?)
        """,
        (channel_account_id, channel_account_id),
    ).fetchone()
    return bool(row[0])


def is_known_conversation(
    conn: sqlite3.Connection, channel_account_id: int, conversation_external_id: str
) -> bool:
    """Whether a channel conversation was already queued or stored."""
    row = conn.execute(
        """
        SELECT EXISTS (SELECT 1 FROM inbound_queue
                       WHERE channel_account_id = ? AND conversation_external_id = ?)
            OR EXISTS (SELECT 1 FROM conversations
                       WHERE channel_account_id = ? AND external_id = ?)
        """,
        (channel_account_id, conversation_external_id, channel_account_id, conversation_external_id),
    ).fetchone()
    return bool(row[0])


def last_known_message_id(
    conn: sqlite3.Connection, channel_account_id: int, conversation_external_id: str
) -> str | None:
    """Channel id of the newest message we already have for a conversation.

    Looks at the stored messages first and then at the queue, because old
    ``done`` rows of the queue can be deleted. ``None`` if there are none.
    """
    row = conn.execute(
        """
        SELECT m.external_id
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.channel_account_id = ? AND c.external_id = ? AND m.external_id IS NOT NULL
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT 1
        """,
        (channel_account_id, conversation_external_id),
    ).fetchone()
    if row is not None:
        return row[0]
    row = conn.execute(
        """
        SELECT message_external_id FROM inbound_queue
        WHERE channel_account_id = ? AND conversation_external_id = ?
        ORDER BY enqueued_at DESC, id DESC
        LIMIT 1
        """,
        (channel_account_id, conversation_external_id),
    ).fetchone()
    return row[0] if row is not None else None

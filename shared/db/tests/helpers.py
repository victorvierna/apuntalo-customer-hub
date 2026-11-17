"""Test helpers: a temporary database with the real schema, and invented data.

Every id, name and text is invented. Never put real customer data here.
"""

import contextlib
import io
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from shared.db.connection import connect, to_db_time
from shared.db.init_db import init_db
from shared.types.messages import ChannelConversation, ChannelMessage, ContentType, Direction

T0 = datetime(2026, 11, 17, 10, 0, 0, tzinfo=UTC)
THREAD_ID = "340282366841710300000000000000000000001"
OUR_USER_ID = "100"


class DatabaseTestCase(unittest.TestCase):
    """Each test gets a fresh database file created by ``init_db``."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "test.db"
        with contextlib.redirect_stdout(io.StringIO()):
            init_db(path)
        self.conn = connect(path)
        self.addCleanup(self.conn.close)

    def add_account(self, handle: str = "apuntalo_a", external_id: str = "111") -> int:
        return self.conn.execute(
            """
            INSERT INTO channel_accounts (channel, external_id, handle, created_at)
            VALUES ('instagram', ?, ?, ?) RETURNING id
            """,
            (external_id, handle, to_db_time(T0)),
        ).fetchone()["id"]

    def count(self, table: str, where: str = "1", params: tuple = ()) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]

    def row(self, sql: str, params: tuple = ()) -> sqlite3.Row:
        return self.conn.execute(sql, params).fetchone()


def conversation(
    thread_id: str = THREAD_ID,
    participants: tuple[str, ...] = ("cliente.prueba",),
    title: str = "Cliente Prueba",
) -> ChannelConversation:
    return ChannelConversation(
        channel="instagram",
        external_id=thread_id,
        title=title,
        participants=participants,
        last_activity_at=T0,
    )


def message(
    external_id: str,
    body: str | None = "hola",
    sender: str = "900",
    direction: Direction = Direction.IN,
    content_type: ContentType = ContentType.TEXT,
    thread_id: str = THREAD_ID,
    created_at: datetime = T0,
) -> ChannelMessage:
    return ChannelMessage(
        channel="instagram",
        external_id=external_id,
        conversation_external_id=thread_id,
        sender_external_id=OUR_USER_ID if direction is Direction.OUT else sender,
        direction=direction,
        content_type=content_type,
        body=body,
        created_at=created_at,
    )

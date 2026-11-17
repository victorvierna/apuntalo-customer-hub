"""Opening the database, transactions and the date format.

Every module connects through ``connect()`` so the per-connection settings of
``docs/architecture/database.md`` (section 8) are always applied.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from shared.db.init_db import get_db_path


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Opens the database (``DATABASE_PATH`` or the default path).

    The connection is in autocommit mode: group writes with ``transaction()``.
    Rows can be read by column name (``row["id"]``).
    """
    conn = sqlite3.connect(db_path or get_db_path(), isolation_level=None)
    conn.row_factory = sqlite3.Row
    # WAL is stored in the file (init_db sets it); these two are per connection.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """All or nothing: if anything inside fails, nothing is written.

    ``BEGIN IMMEDIATE`` takes the write lock at the start, so two processes
    never read the same pending rows and both act on them.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def to_db_time(moment: datetime) -> str:
    """ISO-8601 in UTC, always with milliseconds: ``2026-11-10T14:30:00.000Z``.

    Always the same format, so dates sort correctly as text (``...:00Z`` would
    sort after ``...:00.500Z``).
    """
    if moment.tzinfo is None:
        raise ValueError("Dates must be timezone-aware.")
    moment = moment.astimezone(UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"

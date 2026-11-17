"""People, their identities in each channel, and blocks (``database.md`` 6.2 and 6.11)."""

import sqlite3


def find_contact(conn: sqlite3.Connection, channel: str, external_id: str) -> sqlite3.Row | None:
    """The identity with this id in the channel: ``id``, ``person_id``, ``username``."""
    return conn.execute(
        "SELECT id, person_id, username FROM contacts WHERE channel = ? AND external_id = ?",
        (channel, external_id),
    ).fetchone()


def find_person_by_username(conn: sqlite3.Connection, channel: str, username: str) -> int | None:
    """Person of the most recent identity with this username in the channel."""
    row = conn.execute(
        """
        SELECT person_id FROM contacts
        WHERE channel = ? AND username = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (channel, username),
    ).fetchone()
    return row["person_id"] if row else None


def create_person(conn: sqlite3.Connection, display_name: str | None, now: str) -> int:
    return conn.execute(
        "INSERT INTO people (display_name, created_at) VALUES (?, ?) RETURNING id",
        (display_name, now),
    ).fetchone()["id"]


def create_contact(
    conn: sqlite3.Connection,
    person_id: int,
    channel: str,
    external_id: str,
    username: str | None,
    display_name: str | None,
    now: str,
) -> int:
    return conn.execute(
        """
        INSERT INTO contacts (person_id, channel, external_id, username, display_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (person_id, channel, external_id, username, display_name, now),
    ).fetchone()["id"]


def update_username(conn: sqlite3.Connection, contact_id: int, username: str) -> None:
    conn.execute("UPDATE contacts SET username = ? WHERE id = ?", (username, contact_id))


def has_active_block(conn: sqlite3.Connection, person_id: int) -> bool:
    """Only ``active`` blocks count: a router proposal blocks nobody until confirmed."""
    row = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM blocks WHERE person_id = ? AND status = 'active')",
        (person_id,),
    ).fetchone()
    return bool(row[0])

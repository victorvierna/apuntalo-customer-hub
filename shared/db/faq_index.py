"""Full-text index of the help guides (SQLite FTS5), kept in memory.

It is not stored in the main database: it is rebuilt from ``data/faqs/`` every
time the program starts (a few milliseconds), so it can never be older than the
guides. ``docs/modules/rag.md`` explains why.
"""

import sqlite3
from collections.abc import Iterable

# unicode61 lowercases; remove_diacritics 2 makes "cítas", "Citas" and "citas"
# the same word. Queries go through the same tokenizer.
_SCHEMA = """
CREATE VIRTUAL TABLE faq_chunks USING fts5(
  ref UNINDEXED,
  title,
  body,
  tokenize = 'unicode61 remove_diacritics 2'
);
"""


def create_index() -> sqlite3.Connection:
    """Opens an empty in-memory index. Fails if this SQLite has no FTS5."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(_SCHEMA)
    except sqlite3.OperationalError as exc:
        conn.close()
        raise RuntimeError(
            f"This SQLite ({sqlite3.sqlite_version}) was built without FTS5, which the RAG needs."
        ) from exc
    return conn


def add_chunks(conn: sqlite3.Connection, rows: Iterable[tuple[str, str, str]]) -> None:
    """Adds ``(ref, title, body)`` rows. ``title`` and ``body`` are plain text."""
    conn.executemany("INSERT INTO faq_chunks (ref, title, body) VALUES (?, ?, ?)", rows)


def search(conn: sqlite3.Connection, match: str, limit: int) -> list[tuple[str, float]]:
    """Runs an FTS5 ``MATCH`` query. Returns ``(ref, score)``, best first.

    FTS5's ``bm25()`` is negative (more negative = better); the sign is flipped
    so that a higher score means more relevant.
    """
    rows = conn.execute(
        """
        SELECT ref, -bm25(faq_chunks) AS score
        FROM faq_chunks
        WHERE faq_chunks MATCH ?
        ORDER BY score DESC, ref
        LIMIT ?
        """,
        (match, limit),
    ).fetchall()
    return [(ref, score) for ref, score in rows]

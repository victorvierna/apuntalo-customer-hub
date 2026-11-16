"""Create the SQLite database with the schema in docs/architecture/database.md.

Usage:
    python shared/db/init_db.py

The database path is read from the DATABASE_PATH environment variable.
If it is not set, storage/apuntalo-marketing-platform.db is used.
Relative paths are resolved against the repository root.

Running it again on an existing database is safe: the schema version is
stored in PRAGMA user_version and the schema is only applied once.
"""

import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "storage" / "apuntalo-marketing-platform.db"

SCHEMA_VERSION = 1

# STRICT tables require SQLite 3.37 or newer.
MIN_SQLITE_VERSION = (3, 37, 0)

SCHEMA = """
CREATE TABLE channel_accounts (
  id           INTEGER PRIMARY KEY,
  channel      TEXT NOT NULL,
  external_id  TEXT NOT NULL,
  handle       TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  UNIQUE (channel, external_id)
) STRICT;

CREATE TABLE contacts (
  id            INTEGER PRIMARY KEY,
  channel       TEXT NOT NULL,
  external_id   TEXT NOT NULL,
  display_name  TEXT,
  is_customer   INTEGER CHECK (is_customer IN (0, 1)),
  is_blocked    INTEGER NOT NULL DEFAULT 0 CHECK (is_blocked IN (0, 1)),
  created_at    TEXT NOT NULL,
  UNIQUE (channel, external_id)
) STRICT;

-- OPCIONAL / PENDIENTE DE REVISIÓN: puede que no sea necesaria
CREATE TABLE users (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  created_at  TEXT NOT NULL
) STRICT;

CREATE TABLE conversations (
  id                  INTEGER PRIMARY KEY,
  channel_account_id  INTEGER NOT NULL REFERENCES channel_accounts(id),
  contact_id          INTEGER NOT NULL REFERENCES contacts(id),
  status              TEXT NOT NULL DEFAULT 'bot'
                      CHECK (status IN ('bot', 'waiting_human', 'closed')),
  external_id         TEXT NOT NULL,
  last_message_at     TEXT NOT NULL,
  created_at          TEXT NOT NULL,
  UNIQUE (channel_account_id, external_id)
) STRICT;

CREATE TABLE messages (
  id               INTEGER PRIMARY KEY,
  conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
  direction        TEXT NOT NULL CHECK (direction IN ('in', 'out')),
  author           TEXT NOT NULL CHECK (author IN ('contact', 'assistant', 'human')),
  author_user_id   INTEGER REFERENCES users(id),
  content_type     TEXT NOT NULL DEFAULT 'text'
                   CHECK (content_type IN ('text', 'image', 'video', 'audio',
                                          'reaction', 'unsupported')),
  body             TEXT,
  media_path       TEXT,
  external_id      TEXT,
  delivery_status  TEXT CHECK (delivery_status IN ('sent', 'failed')),
  created_at       TEXT NOT NULL,
  UNIQUE (conversation_id, external_id),
  CHECK (content_type <> 'text' OR body IS NOT NULL)
) STRICT;

CREATE TABLE processing_runs (
  id                INTEGER PRIMARY KEY,
  message_id        INTEGER NOT NULL REFERENCES messages(id),
  gateway_result    TEXT NOT NULL
                    CHECK (gateway_result IN ('accepted', 'blocked_injection', 'rate_limited', 'timeout', 'error')),
  intent            TEXT CHECK (intent IN ('faq', 'request', 'out_of_faq')),
  action            TEXT CHECK (action IN ('answer', 'request', 'deny', 'handoff')),
  reply_message_id  INTEGER REFERENCES messages(id),
  error             TEXT,
  started_at        TEXT NOT NULL,
  finished_at       TEXT
) STRICT;

CREATE TABLE model_calls (
  id             INTEGER PRIMARY KEY,
  run_id         INTEGER REFERENCES processing_runs(id),
  purpose        TEXT NOT NULL CHECK (purpose IN ('routing', 'answer', 'summary')),
  provider       TEXT NOT NULL,
  model          TEXT NOT NULL,
  input_tokens   INTEGER,
  output_tokens  INTEGER,
  cost_micros    INTEGER,
  latency_ms     INTEGER,
  created_at     TEXT NOT NULL,
  CHECK (run_id IS NOT NULL OR purpose = 'summary')
) STRICT;

CREATE TABLE conversation_summaries (
  id               INTEGER PRIMARY KEY,
  conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
  last_message_id  INTEGER NOT NULL REFERENCES messages(id),
  summary          TEXT NOT NULL,
  model_call_id    INTEGER NOT NULL REFERENCES model_calls(id),
  created_at       TEXT NOT NULL
) STRICT;

CREATE TABLE faq_retrievals (
  id       INTEGER PRIMARY KEY,
  run_id   INTEGER NOT NULL REFERENCES processing_runs(id),
  faq_ref  TEXT NOT NULL,
  score    REAL,
  rank     INTEGER NOT NULL
) STRICT;

CREATE TABLE handoffs (
  id                 INTEGER PRIMARY KEY,
  conversation_id    INTEGER NOT NULL REFERENCES conversations(id),
  run_id             INTEGER REFERENCES processing_runs(id),
  reason             TEXT NOT NULL
                     CHECK (reason IN ('out_of_faq', 'request', 'low_confidence',
                                       'unsupported_content', 'manual')),
  status             TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'answered', 'closed')),
  assigned_user_id   INTEGER REFERENCES users(id),
  answer_message_id  INTEGER REFERENCES messages(id),
  kb_decision        TEXT CHECK (kb_decision IN ('add', 'skip')),
  created_at         TEXT NOT NULL,
  answered_at        TEXT,
  closed_at          TEXT
) STRICT;

CREATE INDEX idx_messages_conv       ON messages(conversation_id, created_at);
CREATE INDEX idx_conversations_inbox ON conversations(status, last_message_at);
CREATE INDEX idx_handoffs_status     ON handoffs(status, created_at);
CREATE INDEX idx_runs_message        ON processing_runs(message_id);
CREATE INDEX idx_model_calls_run     ON model_calls(run_id);
CREATE INDEX idx_summaries_conv      ON conversation_summaries(conversation_id, created_at);
"""


def get_db_path() -> Path:
    path = Path(os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH))
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def init_db(db_path: Path) -> None:
    if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
        raise RuntimeError(
            f"SQLite {sqlite3.sqlite_version} is too old; "
            f"{'.'.join(map(str, MIN_SQLITE_VERSION))} or newer is required."
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)

    # isolation_level=None: we manage transactions explicitly below.
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        # WAL is stored in the file; foreign_keys and busy_timeout are per
        # connection, so the app must set them again every time it connects.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")

        current = conn.execute("PRAGMA user_version").fetchone()[0]
        if current == SCHEMA_VERSION:
            print(f"Database already at schema version {current}: {db_path}")
            return
        if current != 0:
            raise RuntimeError(
                f"Unexpected schema version {current} in {db_path} "
                f"(this script creates version {SCHEMA_VERSION})."
            )

        # All or nothing: if any statement fails, no table is created.
        conn.executescript(
            f"BEGIN;\n{SCHEMA}\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
        )
        print(f"Database created (schema version {SCHEMA_VERSION}): {db_path}")
    finally:
        conn.close()


def main() -> int:
    try:
        init_db(get_db_path())
    except (RuntimeError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

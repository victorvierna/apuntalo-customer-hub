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

SCHEMA_VERSION = 4

# STRICT tables require SQLite 3.37 or newer, and json_valid() (used to check
# routing_decisions.scores) is built in from 3.38.
MIN_SQLITE_VERSION = (3, 38, 0)

SCHEMA = """
CREATE TABLE channel_accounts (
  id           INTEGER PRIMARY KEY,
  channel      TEXT NOT NULL,
  external_id  TEXT NOT NULL,
  handle       TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  UNIQUE (channel, external_id)
) STRICT;

CREATE TABLE people (
  id            INTEGER PRIMARY KEY,
  display_name  TEXT,
  is_customer   INTEGER CHECK (is_customer IN (0, 1)),
  created_at    TEXT NOT NULL
) STRICT;

CREATE TABLE contacts (
  id            INTEGER PRIMARY KEY,
  person_id     INTEGER NOT NULL REFERENCES people(id),
  channel       TEXT NOT NULL,
  external_id   TEXT NOT NULL,
  username      TEXT CHECK (username = lower(username)),
  display_name  TEXT,
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
  delivery_status  TEXT CHECK (delivery_status IN ('pending', 'sent', 'failed')),
  created_at       TEXT NOT NULL,
  UNIQUE (conversation_id, external_id),
  CHECK (content_type <> 'text' OR body IS NOT NULL)
) STRICT;

CREATE TABLE processing_runs (
  id                INTEGER PRIMARY KEY,
  gateway_result    TEXT NOT NULL
                    CHECK (gateway_result IN ('accepted', 'store_only', 'unsupported_content',
                                              'human_owned', 'blocked_contact',
                                              'blocked_injection', 'rate_limited', 'error')),
  intent            TEXT CHECK (intent IN ('faq', 'request', 'out_of_faq')),
  topic             TEXT,
  complexity        REAL CHECK (complexity BETWEEN 0 AND 1),
  action            TEXT CHECK (action IN ('answer', 'request', 'deny', 'handoff')),
  tier              TEXT CHECK (tier IN ('slm', 'llm', 'none')),
  decided_by        TEXT CHECK (decided_by IN ('rule', 'classifier', 'arbiter')),
  output_result     TEXT CHECK (output_result IN ('passed', 'no_grounding', 'rejected')),
  outcome           TEXT CHECK (outcome IN ('replied', 'denied', 'handed_off',
                                            'stored_only', 'failed')),
  reply_message_id  INTEGER REFERENCES messages(id),
  error             TEXT,
  started_at        TEXT NOT NULL,
  finished_at       TEXT,
  CHECK (gateway_result = 'accepted' OR action IS NULL),
  CHECK (action IS NULL OR (tier IS NOT NULL AND decided_by IS NOT NULL)),
  CHECK (action <> 'answer' OR tier IN ('slm', 'llm')),
  CHECK (action NOT IN ('deny', 'handoff') OR tier = 'none'),
  CHECK (finished_at IS NULL OR outcome IS NOT NULL)
) STRICT;

CREATE TABLE inbound_queue (
  id               INTEGER PRIMARY KEY,
  message_id       INTEGER NOT NULL UNIQUE REFERENCES messages(id),
  conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
  status           TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'processing', 'done', 'failed')),
  attempts         INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  run_id           INTEGER REFERENCES processing_runs(id),
  error            TEXT,
  enqueued_at      TEXT NOT NULL,
  started_at       TEXT,
  finished_at      TEXT,
  CHECK (status = 'pending' OR started_at IS NOT NULL),
  CHECK (status NOT IN ('done', 'failed') OR finished_at IS NOT NULL),
  CHECK (status <> 'done' OR run_id IS NOT NULL)
) STRICT;

CREATE TABLE run_messages (
  run_id      INTEGER NOT NULL REFERENCES processing_runs(id),
  message_id  INTEGER NOT NULL REFERENCES messages(id),
  PRIMARY KEY (run_id, message_id)
) STRICT;

CREATE TABLE model_calls (
  id             INTEGER PRIMARY KEY,
  run_id         INTEGER REFERENCES processing_runs(id),
  purpose        TEXT NOT NULL CHECK (purpose IN ('routing', 'answer', 'summary')),
  provider       TEXT NOT NULL,
  model          TEXT NOT NULL,
  tier           TEXT NOT NULL CHECK (tier IN ('slm', 'llm')),
  status         TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'timeout', 'error')),
  is_fallback    INTEGER NOT NULL DEFAULT 0 CHECK (is_fallback IN (0, 1)),
  input_tokens   INTEGER,
  output_tokens  INTEGER,
  cost_micros    INTEGER,
  latency_ms     INTEGER,
  created_at     TEXT NOT NULL,
  CHECK (run_id IS NOT NULL OR purpose = 'summary')
) STRICT;

CREATE TABLE routing_decisions (
  id              INTEGER PRIMARY KEY,
  run_id          INTEGER NOT NULL REFERENCES processing_runs(id),
  phase           TEXT NOT NULL CHECK (phase IN ('rule', 'classifier', 'arbiter')),
  intent          TEXT CHECK (intent IN ('faq', 'request', 'out_of_faq')),
  topic           TEXT,
  complexity      REAL CHECK (complexity BETWEEN 0 AND 1),
  action          TEXT NOT NULL CHECK (action IN ('answer', 'request', 'deny', 'handoff')),
  tier            TEXT NOT NULL CHECK (tier IN ('slm', 'llm', 'none')),
  confidence      REAL CHECK (confidence BETWEEN 0 AND 1),
  threshold       REAL CHECK (threshold BETWEEN 0 AND 1),
  scores          TEXT CHECK (scores IS NULL OR json_valid(scores)),
  router_version  TEXT NOT NULL,
  latency_ms      INTEGER NOT NULL,
  model_call_id   INTEGER REFERENCES model_calls(id),
  created_at      TEXT NOT NULL,
  UNIQUE (run_id, phase),
  CHECK (phase <> 'classifier'
         OR (confidence IS NOT NULL AND threshold IS NOT NULL AND scores IS NOT NULL)),
  CHECK (phase <> 'arbiter' OR model_call_id IS NOT NULL)
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

CREATE TABLE blocks (
  id                  INTEGER PRIMARY KEY,
  person_id           INTEGER NOT NULL REFERENCES people(id),
  source              TEXT NOT NULL CHECK (source IN ('channel', 'human', 'router')),
  status              TEXT NOT NULL
                      CHECK (status IN ('proposed', 'active', 'rejected', 'lifted')),
  channel_account_id  INTEGER REFERENCES channel_accounts(id),
  run_id              INTEGER REFERENCES processing_runs(id),
  reason              TEXT,
  created_at          TEXT NOT NULL,
  decided_at          TEXT,
  lifted_at           TEXT,
  CHECK (source <> 'channel' OR channel_account_id IS NOT NULL),
  CHECK (source <> 'router' OR (run_id IS NOT NULL AND reason IS NOT NULL)),
  CHECK (status NOT IN ('proposed', 'rejected') OR source = 'router'),
  CHECK (status <> 'lifted' OR lifted_at IS NOT NULL)
) STRICT;

CREATE INDEX idx_messages_conv       ON messages(conversation_id, created_at);
CREATE INDEX idx_conversations_inbox ON conversations(status, last_message_at);
CREATE INDEX idx_handoffs_status     ON handoffs(status, created_at);
CREATE INDEX idx_run_messages_msg    ON run_messages(message_id);
CREATE INDEX idx_queue_pending       ON inbound_queue(conversation_id, enqueued_at)
                                     WHERE status = 'pending';
CREATE INDEX idx_queue_processing    ON inbound_queue(started_at) WHERE status = 'processing';
CREATE INDEX idx_messages_outbox     ON messages(created_at) WHERE delivery_status = 'pending';
CREATE INDEX idx_model_calls_run     ON model_calls(run_id);
CREATE INDEX idx_summaries_conv      ON conversation_summaries(conversation_id, created_at);
CREATE INDEX idx_contacts_person     ON contacts(person_id);
CREATE INDEX idx_contacts_username   ON contacts(channel, username);
CREATE INDEX idx_blocks_active       ON blocks(person_id) WHERE status = 'active';
CREATE INDEX idx_blocks_proposed     ON blocks(created_at) WHERE status = 'proposed';
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
            # There are no migrations yet: older versions only exist in local
            # test databases without real data, which can be recreated.
            raise RuntimeError(
                f"Unexpected schema version {current} in {db_path} "
                f"(this script creates version {SCHEMA_VERSION}). "
                "If it is a local database without real data, delete it and run "
                "this script again."
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

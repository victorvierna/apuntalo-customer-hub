"""Reads the inbound queue and runs each ready burst through the gateway.

How often ``run_once`` is called, and how the process is started, is still
open (``gateway.md``, open decision 1).
"""

import logging
import sqlite3
from datetime import UTC, datetime

from shared.db.connection import to_db_time, transaction
from shared.db.queue import pending_burst, ready_conversations, record_failure
from shared.types.gateway import GatewayDecision

from .pipeline import process_burst

logger = logging.getLogger(__name__)

# When a burst is over (QUIET_PERIOD, MAX_WAIT) is decided in shared/db/queue.py,
# because the channel readers use the same values.

MAX_ATTEMPTS = 3
"""Failed attempts before a burst is marked ``failed``."""


def run_once(conn: sqlite3.Connection, now: datetime | None = None) -> list[GatewayDecision]:
    """Processes every conversation whose burst is ready. Returns the decisions taken.

    Each burst has its own transaction: a burst that fails is rolled back
    (its messages are not stored and its rows stay pending), counts a failed
    attempt, and does not stop the others.
    """
    now = now or datetime.now(UTC)
    now_text = to_db_time(now)
    decisions = []
    for account_id, conversation_external_id in ready_conversations(conn, now):
        try:
            with transaction(conn):
                # Read again under the write lock: another process may have
                # taken this burst in the meantime.
                burst = pending_burst(conn, account_id, conversation_external_id)
                decision = process_burst(conn, burst, now_text) if burst else None
        except Exception as exc:
            logger.exception(
                "Gateway failed on conversation %s of account %s",
                conversation_external_id,
                account_id,
            )
            with transaction(conn):
                record_failure(
                    conn,
                    account_id,
                    conversation_external_id,
                    f"{type(exc).__name__}: {exc}",
                    now_text,
                    MAX_ATTEMPTS,
                )
            continue
        if decision is not None:
            decisions.append(decision)
    return decisions

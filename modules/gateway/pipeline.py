"""One burst through the whole gateway: store, check, record.

``process_burst`` must run inside a transaction (``worker.py`` opens it). The
queue rows are marked done in that same transaction, and an accepted burst
leaves an open processing run. So a crash either loses nothing (rollback: the
rows are still pending) or leaves the run open for whoever answers to resume.
"""

import sqlite3

from shared.db.conversations import create_handoff, set_conversation_status
from shared.db.queue import mark_done
from shared.db.runs import create_run
from shared.types.gateway import GatewayDecision, GatewayResult, Outcome
from shared.types.queue import QueuedMessage

from .checks import CHECKS, BurstContext
from .ingest import store_burst

# Results that end the run in the gateway. ACCEPTED is not here: its run stays
# open until it is answered.
_OUTCOMES = {
    GatewayResult.STORE_ONLY: Outcome.STORED_ONLY,
    GatewayResult.UNSUPPORTED_CONTENT: Outcome.HANDED_OFF,
    GatewayResult.HUMAN_OWNED: Outcome.STORED_ONLY,
    GatewayResult.BLOCKED_CONTACT: Outcome.STORED_ONLY,
}


def process_burst(
    conn: sqlite3.Connection, burst: list[QueuedMessage], now: str
) -> GatewayDecision | None:
    """Returns the decision, or None if there was nothing new to process."""
    queue_ids = [item.queue_id for item in burst]

    stored = store_burst(conn, burst, now)
    if isinstance(stored, str):
        mark_done(conn, queue_ids, now, note=stored)
        return None
    mark_done(conn, queue_ids, now)

    # Re-reads, outgoing messages and history: stored, nothing to decide.
    if not stored.fresh:
        return None
    assert stored.identity is not None  # fresh messages are incoming

    status = stored.conversation_status
    if status == "closed":
        # Pending definition (gateway.md, open decision 3): for now a new
        # message reopens the conversation.
        set_conversation_status(conn, stored.conversation_id, "bot")
        status = "bot"

    ctx = BurstContext(
        person_id=stored.identity.person_id,
        conversation_status=status,
        messages=tuple(message for _, message in stored.fresh),
    )
    result = GatewayResult.ACCEPTED
    for check in CHECKS:
        stop = check(conn, ctx)
        if stop is not None:
            result = stop
            break

    message_ids = [message_id for message_id, _ in stored.fresh]
    run_id = create_run(conn, result, message_ids, now, _OUTCOMES.get(result))

    if result is GatewayResult.UNSUPPORTED_CONTENT:
        create_handoff(conn, stored.conversation_id, run_id, "unsupported_content", now)
        set_conversation_status(conn, stored.conversation_id, "waiting_human")

    return GatewayDecision(
        run_id=run_id,
        result=result,
        conversation_id=stored.conversation_id,
        person_id=stored.identity.person_id,
        is_new_person=stored.identity.is_new_person,
        is_new_identity=stored.identity.is_new_identity,
        message_ids=tuple(message_ids),
    )

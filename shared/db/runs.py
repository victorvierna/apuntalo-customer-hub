"""Processing runs and their messages (``database.md`` 6.5 and 6.12)."""

import sqlite3

from shared.types.gateway import GatewayResult, Outcome


def create_run(
    conn: sqlite3.Connection,
    gateway_result: GatewayResult,
    message_ids: list[int],
    now: str,
    outcome: Outcome | None = None,
) -> int:
    """Creates a processing run with its messages.

    With ``outcome`` the run is finished right away (the gateway stopped it).
    Without it, it stays open (``finished_at`` empty) until whoever comes next
    answers: that is how a pending reply survives a crash.
    """
    run_id = conn.execute(
        """
        INSERT INTO processing_runs (gateway_result, outcome, started_at, finished_at)
        VALUES (?, ?, ?, ?)
        RETURNING id
        """,
        (
            gateway_result.value,
            outcome.value if outcome else None,
            now,
            now if outcome else None,
        ),
    ).fetchone()["id"]
    conn.executemany(
        "INSERT INTO run_messages (run_id, message_id) VALUES (?, ?)",
        [(run_id, message_id) for message_id in message_ids],
    )
    return run_id


def unfinished_accepted_runs(conn: sqlite3.Connection) -> list[int]:
    """Runs the gateway accepted that nobody has answered yet, oldest first.

    This is the "pending to answer" list: after a crash, whoever answers
    (the router, once it exists) resumes from here.
    """
    rows = conn.execute(
        """
        SELECT id FROM processing_runs
        WHERE gateway_result = 'accepted' AND finished_at IS NULL
        ORDER BY started_at, id
        """
    ).fetchall()
    return [row["id"] for row in rows]

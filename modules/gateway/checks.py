"""Steps 5 to 7 of the gateway: may the assistant answer? (``gateway.md`` section 4).

Each check returns a result to stop the burst, or None to let it continue.
They run in the order of ``CHECKS``; adding one (rate limit, prompt
injection...) is adding it to that list.
"""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from modules.handoff.policy import Handling, decide
from shared.db.contacts import has_active_block
from shared.types.gateway import GatewayResult
from shared.types.messages import ChannelMessage


@dataclass(frozen=True, slots=True)
class BurstContext:
    person_id: int
    conversation_status: str
    messages: tuple[ChannelMessage, ...]
    """New incoming messages of the burst."""


Check = Callable[[sqlite3.Connection, BurstContext], GatewayResult | None]


def reject_if_blocked(conn: sqlite3.Connection, ctx: BurstContext) -> GatewayResult | None:
    """Blocks belong to the person, so a block in any account or channel counts."""
    if has_active_block(conn, ctx.person_id):
        return GatewayResult.BLOCKED_CONTACT
    return None


def stop_if_human_owned(conn: sqlite3.Connection, ctx: BurstContext) -> GatewayResult | None:
    if ctx.conversation_status == "waiting_human":
        return GatewayResult.HUMAN_OWNED
    return None


def apply_content_policy(conn: sqlite3.Connection, ctx: BurstContext) -> GatewayResult | None:
    """The most restrictive handling of the burst wins.

    A question with a photo the assistant cannot see cannot be answered well,
    so one ``HANDOFF`` hands off the whole burst. Reactions next to text are
    ignored.
    """
    handlings = {decide(message) for message in ctx.messages}
    if Handling.HANDOFF in handlings:
        return GatewayResult.UNSUPPORTED_CONTENT
    if Handling.ASSISTANT in handlings:
        return None
    return GatewayResult.STORE_ONLY


CHECKS: tuple[Check, ...] = (reject_if_blocked, stop_if_human_owned, apply_content_policy)

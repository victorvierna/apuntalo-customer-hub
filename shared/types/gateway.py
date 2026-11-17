"""What the gateway decides (``docs/architecture/gateway.md``).

The values are the same as the ``CHECK`` constraints of ``processing_runs`` in
``docs/architecture/database.md`` (section 6.5).
"""

from dataclasses import dataclass
from enum import StrEnum


class GatewayResult(StrEnum):
    ACCEPTED = "accepted"
    """Passes every check and goes to the router."""

    STORE_ONLY = "store_only"
    """Only content nobody has to answer (e.g. a reaction)."""

    UNSUPPORTED_CONTENT = "unsupported_content"
    """Something the assistant cannot read (photo, video, audio...): handed off."""

    HUMAN_OWNED = "human_owned"
    """The conversation is ``waiting_human``: a person handles it."""

    BLOCKED_CONTACT = "blocked_contact"
    """The person has an active block, in any channel or account."""

    BLOCKED_INJECTION = "blocked_injection"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


class Outcome(StrEnum):
    """How a processing run ended (``processing_runs.outcome``)."""

    REPLIED = "replied"
    DENIED = "denied"
    HANDED_OFF = "handed_off"
    STORED_ONLY = "stored_only"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class GatewayDecision:
    """One processed burst: one row of ``processing_runs``."""

    run_id: int
    result: GatewayResult
    conversation_id: int
    person_id: int
    is_new_person: bool
    """First time this person writes to us, through any channel or account."""

    is_new_identity: bool
    """First time from this identity. With ``is_new_person`` false, the person
    already wrote from somewhere else and there is previous context."""

    message_ids: tuple[int, ...]
    """New incoming messages of the burst (``run_messages``), oldest first."""

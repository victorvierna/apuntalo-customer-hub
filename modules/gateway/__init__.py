"""Gateway: the single entry to the core (``docs/architecture/gateway.md``).

Takes the bursts of the inbound queue, stores them and decides whether the
assistant may answer. It never imports anything from ``modules/channels``.

Usage::

    from modules.gateway import run_once
    from shared.db.connection import connect

    decisions = run_once(connect())
"""

from .worker import run_once

__all__ = ["run_once"]

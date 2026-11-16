"""Hands a conversation off to a person when the assistant cannot answer it.

``policy`` decides, from what a message contains, whether the assistant may
try to answer it, a person has to look at it, or it is only stored.
"""

from .policy import POLICY, Handling, decide

__all__ = ["POLICY", "Handling", "decide"]

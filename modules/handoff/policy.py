"""What happens to a message depending on what it contains.

The channel adapters only say *what* a message is (``ContentType``). This file
decides *what to do* with it, so the rule can change without touching any
adapter. To change how a type is handled, change ``POLICY``.

``ASSISTANT`` does not mean the assistant will answer: it still hands off when
the FAQ do not cover the question. It only means the assistant may try.
"""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

from shared.types.messages import ChannelMessage, ContentType, Direction


class Handling(StrEnum):
    ASSISTANT = "assistant"
    """The assistant may try to answer it."""

    HANDOFF = "handoff"
    """A person has to look at it (``handoffs.reason = 'unsupported_content'``)."""

    STORE_ONLY = "store_only"
    """Saved and shown in the dashboard; nobody needs to answer it."""


POLICY: Mapping[ContentType, Handling] = MappingProxyType(
    {
        ContentType.TEXT: Handling.ASSISTANT,
        ContentType.MEDIA: Handling.HANDOFF,
        ContentType.UNSUPPORTED: Handling.HANDOFF,
    }
)


def decide(message: ChannelMessage) -> Handling:
    """How to handle a message read from a channel.

    Outgoing messages (sent by the assistant or by a person) are only stored.
    """
    if message.direction is Direction.OUT:
        return Handling.STORE_ONLY
    return POLICY[message.content_type]

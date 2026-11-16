"""Channel-independent message types.

Every channel adapter (today only ``modules/channels/instagram``) translates what
its channel returns into these types. The rest of the system (gateway, handoff,
database...) only works with them, so it never needs to know which channel a
message came from or how that channel formats its data.

Field names follow the database schema (``docs/architecture/database.md``):
``external_id``, ``direction``, ``content_type``, ``body`` and ``created_at``.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ContentType(StrEnum):
    """What a message contains.

    It only says what the message is. What the system does with each type
    (answer, hand off, only store) is decided in ``modules/handoff/policy.py``.
    """

    TEXT = "text"
    """Plain text."""

    IMAGE = "image"
    """A photo that can be downloaded."""

    VIDEO = "video"
    """A video that can be downloaded."""

    AUDIO = "audio"
    """A voice note. The channel may not let us download it (Instagram does
    not, through instagram-cli 2.1.0)."""

    REACTION = "reaction"
    """A reaction sent as a message, such as a heart. ``body`` is the emoji."""

    UNSUPPORTED = "unsupported"
    """Content the channel does not let us read (voice notes, shared posts,
    reels, links...). ``body`` says what it was."""


class Direction(StrEnum):
    IN = "in"
    """Sent by the contact to one of our accounts."""

    OUT = "out"
    """Sent from one of our accounts (by the assistant or by a person)."""


@dataclass(frozen=True, slots=True)
class ChannelConversation:
    """A conversation as the channel reports it."""

    channel: str
    external_id: str
    """Conversation id in the channel. Needed to read and send messages."""

    title: str
    """Name the channel shows for the conversation."""

    participants: tuple[str, ...]
    """Usernames of the other participants (one in a one-to-one chat)."""

    last_activity_at: datetime
    """Timezone-aware (UTC). Not reliable to detect new messages: see the
    adapter documentation."""


@dataclass(frozen=True, slots=True)
class ChannelMessage:
    """A single message, incoming or outgoing."""

    channel: str
    external_id: str
    """Message id in the channel. Used to avoid storing a message twice."""

    conversation_external_id: str
    sender_external_id: str
    """Stable user id of the sender in the channel (not the username, which
    can change)."""

    direction: Direction
    content_type: ContentType
    body: str | None
    """Text of the message. For ``TEXT`` it is always a string. For
    ``REACTION`` it is the emoji. For
    ``UNSUPPORTED`` it describes what was sent (e.g. ``[Unsupported Type:
    xma_media_share]``) so a person knows what to look at. ``None`` for
    ``IMAGE``, ``VIDEO`` and ``AUDIO``."""

    created_at: datetime
    """When the channel says the message was sent. Timezone-aware (UTC)."""

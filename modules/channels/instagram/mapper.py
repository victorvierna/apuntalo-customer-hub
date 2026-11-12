"""Translates instagram-cli JSON into the common types of ``shared.types``.

Pure functions: they do not run anything, so they are easy to test with saved
examples (``tests/fixtures``).

How each ``itemType`` of instagram-cli is translated (checked against
instagram-cli 2.1.0 and real messages):

    text          -> TEXT         body = the text ("" if empty)
    media         -> MEDIA        photo or video; body = None
    placeholder "[Sent a ❤️]"
                  -> REACTION     body = "❤️"
    anything else -> UNSUPPORTED  body = the description instagram-cli gives,
                                  or "[<itemType>]" if it gives none

"Anything else" includes ``placeholder`` (voice notes, shared posts, reels,
disappearing photos...), ``link`` and ``media_share``. instagram-cli does not
include their content in the JSON, so the assistant cannot use them.

``[Sent a ❤️]`` is the heart sent as a message (Instagram's "like" item). The
reactions to a specific message (long press) are not in the JSON of
instagram-cli 2.1.0 ``read``, so they never reach us.
"""

from datetime import UTC, datetime
from typing import Any

from shared.types.messages import (
    ChannelConversation,
    ChannelMessage,
    ContentType,
    Direction,
)

from .errors import InstagramFormatError

CHANNEL = "instagram"

# Exact text instagram-cli gives to a heart sent as a message. Matched exactly:
# other placeholders also start with "[Sent a" (e.g. "[Sent a link]").
_HEART = "\u2764\ufe0f"
_HEART_PLACEHOLDER = f"[Sent a {_HEART}]"


def to_conversation(raw: Any) -> ChannelConversation:
    """Translates one item of ``instagram-cli inbox``."""
    item = _require_dict(raw, "inbox thread")
    users = item.get("users", [])
    if not isinstance(users, list) or not all(isinstance(u, str) for u in users):
        raise InstagramFormatError("inbox thread: 'users' must be a list of strings.")
    title = item.get("title")
    return ChannelConversation(
        channel=CHANNEL,
        external_id=_require_str(item, "id", "inbox thread"),
        title=title if isinstance(title, str) else "",
        participants=tuple(users),
        last_activity_at=_parse_timestamp(item.get("lastActivity"), "inbox thread"),
    )


def to_message(raw: Any, conversation_external_id: str) -> ChannelMessage:
    """Translates one message of ``instagram-cli read``."""
    item = _require_dict(raw, "message")
    is_outgoing = item.get("isOutgoing")
    if not isinstance(is_outgoing, bool):
        raise InstagramFormatError("message: 'isOutgoing' must be a boolean.")

    item_type = item.get("itemType")
    text = item.get("text")
    text = text if isinstance(text, str) else None

    if item_type == "text":
        content_type, body = ContentType.TEXT, text or ""
    elif item_type == "media":
        content_type, body = ContentType.MEDIA, None
    elif item_type == "placeholder" and text == _HEART_PLACEHOLDER:
        content_type, body = ContentType.REACTION, _HEART
    else:
        content_type, body = ContentType.UNSUPPORTED, text or f"[{item_type}]"

    return ChannelMessage(
        channel=CHANNEL,
        external_id=_require_str(item, "id", "message"),
        conversation_external_id=conversation_external_id,
        # The username in 'read' is often a placeholder ("User_<id>"), so the
        # numeric userId is the only reliable way to identify the sender.
        sender_external_id=_require_str(item, "userId", "message"),
        direction=Direction.OUT if is_outgoing else Direction.IN,
        content_type=content_type,
        body=body,
        created_at=_parse_timestamp(item.get("timestamp"), "message"),
    )


def _require_dict(value: Any, what: str) -> dict:
    if not isinstance(value, dict):
        raise InstagramFormatError(f"{what}: expected an object, got {type(value).__name__}.")
    return value


def _require_str(item: dict, key: str, what: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise InstagramFormatError(f"{what}: '{key}' is missing or empty.")
    return value


def _parse_timestamp(value: Any, what: str) -> datetime:
    """Parses instagram-cli dates (``2026-11-11T08:14:50.694Z``) as UTC."""
    if not isinstance(value, str):
        raise InstagramFormatError(f"{what}: timestamp is missing.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InstagramFormatError(f"{what}: invalid timestamp {value!r}.") from exc
    if parsed.tzinfo is None:
        raise InstagramFormatError(f"{what}: timestamp {value!r} has no timezone.")
    return parsed.astimezone(UTC)

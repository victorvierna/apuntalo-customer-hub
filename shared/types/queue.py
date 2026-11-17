"""What a channel reader puts in the inbound queue (``inbound_queue.payload``).

The reader of each channel (today only Instagram) translates what it reads into
the common types of ``shared.types.messages`` and stores them as JSON. The
gateway reads them back without knowing which channel they came from.
"""

import json
from dataclasses import dataclass
from datetime import datetime

from shared.types.messages import ChannelConversation, ChannelMessage, ContentType, Direction


@dataclass(frozen=True, slots=True)
class QueuedMessage:
    """One row of ``inbound_queue``, already decoded."""

    queue_id: int
    channel_account_id: int
    """Our account that read the message: it came in there and is answered from there."""

    is_backfill: bool
    """History from the first sync: stored, never answered."""

    conversation: ChannelConversation
    message: ChannelMessage


def encode_payload(conversation: ChannelConversation, message: ChannelMessage) -> str:
    return json.dumps(
        {
            "conversation": {
                "channel": conversation.channel,
                "external_id": conversation.external_id,
                "title": conversation.title,
                "participants": list(conversation.participants),
                "last_activity_at": conversation.last_activity_at.isoformat(),
            },
            "message": {
                "channel": message.channel,
                "external_id": message.external_id,
                "conversation_external_id": message.conversation_external_id,
                "sender_external_id": message.sender_external_id,
                "direction": message.direction.value,
                "content_type": message.content_type.value,
                "body": message.body,
                "created_at": message.created_at.isoformat(),
            },
        },
        ensure_ascii=False,
    )


def decode_payload(payload: str) -> tuple[ChannelConversation, ChannelMessage]:
    """Inverse of ``encode_payload``. Raises ``ValueError`` or ``KeyError`` if malformed."""
    data = json.loads(payload)
    conv = data["conversation"]
    msg = data["message"]
    conversation = ChannelConversation(
        channel=conv["channel"],
        external_id=conv["external_id"],
        title=conv["title"],
        participants=tuple(conv["participants"]),
        last_activity_at=_aware(conv["last_activity_at"]),
    )
    message = ChannelMessage(
        channel=msg["channel"],
        external_id=msg["external_id"],
        conversation_external_id=msg["conversation_external_id"],
        sender_external_id=msg["sender_external_id"],
        direction=Direction(msg["direction"]),
        content_type=ContentType(msg["content_type"]),
        body=msg["body"],
        created_at=_aware(msg["created_at"]),
    )
    return conversation, message


def _aware(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError(f"Date without timezone in payload: {text!r}")
    return moment

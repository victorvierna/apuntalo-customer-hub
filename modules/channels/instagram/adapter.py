"""Instagram adapter: what the rest of the system uses to talk to Instagram.

It only talks to Instagram: it does not store anything, decide answers or hand
conversations off. Those are jobs of other modules.

To detect new messages, do not rely on ``unread`` or ``last_activity_at``: a
message request accepted in the app appears as already read and with its old
date. Read the most recent conversations and let the database discard the
messages it already has (``UNIQUE (conversation_id, external_id)``).
"""

import re
from pathlib import Path

from shared.types.messages import ChannelConversation, ChannelMessage

from .cli import InstagramCli
from .errors import InstagramCliError, InstagramFormatError
from .mapper import CHANNEL, to_conversation, to_message

# instagram-cli treats an argument of 20+ digits as a conversation id. Anything
# else is searched by username or title, and can even start a NEW conversation
# with a different person. We only ever pass exact ids.
_CONVERSATION_ID = re.compile(r"\d{20,}")


class InstagramAdapter:
    channel = CHANNEL

    def __init__(self, cli: InstagramCli | None = None) -> None:
        self._cli = cli or InstagramCli()

    def list_conversations(self, limit: int = 20) -> list[ChannelConversation]:
        """Most recent conversations of the main inbox.

        Message requests do not appear until someone accepts them in the app.
        instagram-cli 2.1.0 returns at most 10 conversations whatever the limit.
        """
        _check_limit(limit)
        data = self._cli.run(["inbox", f"--limit={limit}"])
        if not isinstance(data, list):
            raise InstagramFormatError("inbox: 'data' must be a list.")
        return [to_conversation(item) for item in data]

    def read_messages(self, conversation_id: str, limit: int = 20) -> list[ChannelMessage]:
        """Latest messages of a conversation, oldest first.

        Does not mark the conversation as seen, so the contact does not get a
        "Seen" without an answer.
        """
        _check_conversation_id(conversation_id)
        _check_limit(limit)
        data = self._cli.run(["read", conversation_id, f"--limit={limit}"])
        if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
            raise InstagramFormatError("read: 'data.messages' must be a list.")
        return [to_message(item, conversation_id) for item in data["messages"]]

    def send_text(self, conversation_id: str, text: str) -> str:
        """Sends a text message and returns its message id."""
        _check_conversation_id(conversation_id)
        if not text.strip():
            raise ValueError("Refusing to send an empty message.")
        data = self._cli.run(["send", conversation_id, f"--text={text}"])
        if not isinstance(data, dict):
            raise InstagramFormatError("send: 'data' must be an object.")
        message_id = data.get("messageId")
        if data.get("sent") is not True or not isinstance(message_id, str) or not message_id:
            raise InstagramCliError("send: instagram-cli did not confirm the message was sent.")
        return message_id

    def download_media(self, conversation_id: str, message_id: str, destination: Path) -> Path:
        """Downloads the photo or video of a ``MEDIA`` message.

        ``destination`` is a path without extension; instagram-cli adds the
        right one (``.jpg``...). Returns the final path of the file.
        """
        _check_conversation_id(conversation_id)
        if not message_id:
            raise ValueError("message_id is required.")
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = self._cli.run(
            [
                "read",
                conversation_id,
                f"--message-id={message_id}",
                f"--download={destination}",
            ]
        )
        if not isinstance(data, dict) or data.get("downloaded") is not True:
            raise InstagramCliError("download: instagram-cli did not confirm the download.")
        path = data.get("path")
        if not isinstance(path, str) or not path:
            raise InstagramFormatError("download: 'path' is missing.")
        return Path(path)


def _check_conversation_id(conversation_id: str) -> None:
    if not isinstance(conversation_id, str) or not _CONVERSATION_ID.fullmatch(conversation_id):
        raise ValueError(
            f"Invalid Instagram conversation id {conversation_id!r}: "
            "expected the numeric id returned by list_conversations()."
        )


def _check_limit(limit: int) -> None:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError(f"limit must be a positive integer, got {limit!r}.")

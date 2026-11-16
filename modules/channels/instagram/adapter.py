"""Instagram adapter: what the rest of the system uses to talk to Instagram.

It only talks to Instagram: it does not store anything, decide answers or hand
conversations off. Those are jobs of other modules.

To detect new messages, do not rely on ``unread`` or ``last_activity_at``: a
message request accepted in the app appears as already read and with its old
date. Read the most recent conversations and let the database discard the
messages it already has (``UNIQUE (conversation_id, external_id)``).

Do not trust instagram-cli's "sent" either: without our patch
(``patches/instagram-private-api-send-fix.patch``) Instagram silently dropped
13 out of 28 messages in our tests. The adapter logs a warning when it starts
if the patch is missing (``send_patch.py``), and ``send_text`` checks that the
message really appears in the conversation unless told otherwise.
"""

import re
import time
from collections.abc import Callable
from pathlib import Path

from shared.types.messages import ChannelConversation, ChannelMessage

from .cli import InstagramCli
from .errors import InstagramCliError, InstagramDeliveryError, InstagramFormatError
from .mapper import CHANNEL, to_conversation, to_message
from .send_patch import warn_if_send_patch_missing

# instagram-cli treats an argument of 20+ digits as a conversation id. Anything
# else is searched by username or title, and can even start a NEW conversation
# with a different person. We only ever pass exact ids.
_CONVERSATION_ID = re.compile(r"\d{20,}")

# Delivery check after sending: wait, read the conversation, repeat. In tests a
# delivered message was always visible after 2-4 s.
VERIFY_ATTEMPTS = 2
VERIFY_DELAY_SECONDS = 2.0
VERIFY_READ_LIMIT = 10


class InstagramAdapter:
    channel = CHANNEL

    def __init__(
        self,
        cli: InstagramCli | None = None,
        sleep: Callable[[float], None] = time.sleep,
        check_send_patch: bool = True,
    ) -> None:
        """
        Args:
            cli: How to run instagram-cli. Defaults to ``instagram-cli`` in PATH
                with the account that logged in last.
            sleep: Waiting function used by the delivery check. Only tests
                change it.
            check_send_patch: Log a warning if instagram-cli is installed
                without our send fix. Only tests turn it off.
        """
        self._cli = cli or InstagramCli()
        self._sleep = sleep
        if check_send_patch:
            warn_if_send_patch_missing(self._cli.executable)

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

    def send_text(self, conversation_id: str, text: str, verify: bool = True) -> str:
        """Sends a text message and returns its message id.

        With ``verify=True`` (default) it then reads the conversation to check
        the message is really there, which adds ~6-12 s. With ``verify=False``
        it returns right away; check later with ``is_delivered``.

        Raises:
            InstagramDeliveryError: the message was not found after sending, or
                the check itself failed. Mark it as failed and let a person
                look; do not resend automatically or the contact may get it
                twice.
        """
        _check_conversation_id(conversation_id)
        if not text.strip():
            raise ValueError("Refusing to send an empty message.")
        data = self._cli.run(["send", conversation_id, f"--text={text}"])
        if not isinstance(data, dict):
            raise InstagramFormatError("send: 'data' must be an object.")
        message_id = data.get("messageId")
        if data.get("sent") is not True or not isinstance(message_id, str) or not message_id:
            raise InstagramCliError("send: instagram-cli did not confirm the message was sent.")
        if verify:
            self._confirm_delivery(conversation_id, message_id)
        return message_id

    def is_delivered(self, conversation_id: str, message_id: str) -> bool:
        """Whether a sent message appears among the latest of the conversation."""
        messages = self.read_messages(conversation_id, limit=VERIFY_READ_LIMIT)
        return any(message.external_id == message_id for message in messages)

    def _confirm_delivery(self, conversation_id: str, message_id: str) -> None:
        for _ in range(VERIFY_ATTEMPTS):
            self._sleep(VERIFY_DELAY_SECONDS)
            try:
                if self.is_delivered(conversation_id, message_id):
                    return
            except InstagramCliError as exc:
                raise InstagramDeliveryError(
                    f"Message {message_id} was sent but delivery could not be checked: {exc}",
                    message_id,
                ) from exc
        raise InstagramDeliveryError(
            f"Message {message_id} was reported as sent but does not appear in the conversation.",
            message_id,
        )

    def download_media(self, conversation_id: str, message_id: str, destination: Path) -> Path:
        """Downloads the photo or video of an ``IMAGE`` or ``VIDEO`` message.

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

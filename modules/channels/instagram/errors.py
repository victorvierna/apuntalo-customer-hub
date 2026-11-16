"""Errors raised by the Instagram adapter.

They all inherit from ``InstagramCliError`` so callers can catch every adapter
failure at once, or only the ones they can act on (for example, an expired
session means a person has to log in again).
"""


class InstagramCliError(Exception):
    """instagram-cli failed or returned something we cannot use."""


class InstagramCliNotFoundError(InstagramCliError):
    """The instagram-cli executable is not installed or not in PATH."""


class InstagramCliTimeoutError(InstagramCliError):
    """instagram-cli did not answer in time."""


class InstagramAuthError(InstagramCliError):
    """There is no valid session, or Instagram asks for a verification.

    The adapter cannot fix this by itself: a person has to run
    ``instagram-cli auth login`` in an interactive terminal.
    """


class InstagramDeliveryError(InstagramCliError):
    """instagram-cli said the message was sent, but it never appeared in the
    conversation.

    Seen in real tests: Instagram silently drops some messages sent through
    instagram-cli (5 out of 13, at random). The caller should mark the message
    as ``delivery_status = 'failed'`` and let a person know.
    """

    def __init__(self, message: str, message_id: str) -> None:
        super().__init__(message)
        self.message_id = message_id


class InstagramFormatError(InstagramCliError):
    """instagram-cli answered, but not in the format we expect.

    Usually means instagram-cli changed its JSON output after an update.
    """

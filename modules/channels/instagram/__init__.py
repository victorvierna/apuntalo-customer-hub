"""Instagram channel adapter, built on top of instagram-cli.

Usage::

    from modules.channels.instagram import InstagramAdapter

    instagram = InstagramAdapter()
    for conversation in instagram.list_conversations():
        messages = instagram.read_messages(conversation.external_id)

See ``docs/modules/instagram.md``.
"""

from .adapter import InstagramAdapter
from .cli import InstagramCli
from .errors import (
    InstagramAuthError,
    InstagramCliError,
    InstagramCliNotFoundError,
    InstagramCliTimeoutError,
    InstagramDeliveryError,
    InstagramFormatError,
)

__all__ = [
    "InstagramAdapter",
    "InstagramAuthError",
    "InstagramCli",
    "InstagramCliError",
    "InstagramCliNotFoundError",
    "InstagramCliTimeoutError",
    "InstagramDeliveryError",
    "InstagramFormatError",
]

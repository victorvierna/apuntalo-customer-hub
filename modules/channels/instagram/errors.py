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


class InstagramFormatError(InstagramCliError):
    """instagram-cli answered, but not in the format we expect.

    Usually means instagram-cli changed its JSON output after an update.
    """

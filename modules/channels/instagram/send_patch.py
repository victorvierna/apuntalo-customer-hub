"""Checks that our send fix is applied to the installed instagram-cli.

Without ``patches/instagram-private-api-send-fix.patch`` Instagram silently
drops some of the messages we send. Reinstalling or updating instagram-cli
removes the patch without any error, so the adapter checks it when it starts
and logs a warning if it is missing. ``install.sh`` installs instagram-cli
with the patch applied.

The check looks for the ``// apuntalo:`` comments the patch adds to the
library file. It only reads that file: it never runs instagram-cli.
"""

import logging
import shutil
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

# File the patch changes, relative to the folder that holds ``node_modules``.
PATCHED_FILE = Path(
    "node_modules/instagram-private-api/dist/repositories/direct-thread.repository.js"
)
MARKER = "// apuntalo:"

_INSTALL_HINT = "Run modules/channels/instagram/install.sh (see docs/modules/instagram.md)."


class PatchStatus(StrEnum):
    APPLIED = "applied"
    MISSING = "missing"
    UNKNOWN = "unknown"
    """instagram-cli or the library file could not be found or read."""


def find_patched_file(executable: str) -> Path | None:
    """Path of the library file the patch changes, or ``None`` if not found.

    Follows the ``instagram-cli`` link to its package and looks upwards for
    ``node_modules/instagram-private-api``, where npm installs it.
    """
    found = shutil.which(executable)
    if found is None:
        return None
    for folder in Path(found).resolve().parents:
        candidate = folder / PATCHED_FILE
        if candidate.is_file():
            return candidate
    return None


def send_patch_status(executable: str) -> PatchStatus:
    target = find_patched_file(executable)
    if target is None:
        return PatchStatus.UNKNOWN
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return PatchStatus.UNKNOWN
    return PatchStatus.APPLIED if MARKER in content else PatchStatus.MISSING


def warn_if_send_patch_missing(executable: str) -> PatchStatus:
    """Logs a warning unless the patch is applied, and returns the status."""
    status = send_patch_status(executable)
    if status is PatchStatus.MISSING:
        logger.warning(
            "instagram-cli is installed WITHOUT our send fix: Instagram may silently "
            "drop sent messages (send_text still detects them). %s",
            _INSTALL_HINT,
        )
    elif status is PatchStatus.UNKNOWN:
        logger.warning(
            "Could not check whether our send fix is applied to '%s'. %s",
            executable,
            _INSTALL_HINT,
        )
    return status

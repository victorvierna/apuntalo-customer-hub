"""The check that warns when instagram-cli is installed without our send fix.

Builds a fake npm install in a temporary folder, with the same layout as a real
one: ``bin/instagram-cli`` is a link to the package's ``dist/cli.js``.
"""

import os
import tempfile
import unittest
from pathlib import Path

from modules.channels.instagram import InstagramAdapter, InstagramCli
from modules.channels.instagram.send_patch import (
    PATCHED_FILE,
    PatchStatus,
    send_patch_status,
    warn_if_send_patch_missing,
)

from .helpers import FakeRunner

LOGGER = "modules.channels.instagram.send_patch"
PATCHED = "const mutationToken = `${Date.now()}`; // apuntalo: numeric, time-based id\n"
UNPATCHED = "const mutationToken = new Chance().guid();\n"


class FakeInstall:
    """A fake ``npm install -g --prefix <tmp> @i7m/instagram-cli``."""

    def __init__(self, library_content: str | None):
        self._tmp = tempfile.TemporaryDirectory()
        prefix = Path(self._tmp.name)
        package = prefix / "lib/node_modules/@i7m/instagram-cli"
        cli = package / "dist/cli.js"
        cli.parent.mkdir(parents=True)
        cli.write_text("#!/usr/bin/env node\n")
        cli.chmod(0o755)
        self.executable = prefix / "bin/instagram-cli"
        self.executable.parent.mkdir()
        os.symlink(cli, self.executable)
        if library_content is not None:
            library = package / PATCHED_FILE
            library.parent.mkdir(parents=True)
            library.write_text(library_content)

    def cleanup(self):
        self._tmp.cleanup()


class SendPatchStatusTest(unittest.TestCase):
    def status_for(self, library_content):
        install = FakeInstall(library_content)
        self.addCleanup(install.cleanup)
        return send_patch_status(str(install.executable))

    def test_patched_library_is_applied(self):
        self.assertEqual(self.status_for(PATCHED), PatchStatus.APPLIED)

    def test_original_library_is_missing_the_patch(self):
        self.assertEqual(self.status_for(UNPATCHED), PatchStatus.MISSING)

    def test_library_not_found_is_unknown(self):
        self.assertEqual(self.status_for(None), PatchStatus.UNKNOWN)

    def test_instagram_cli_not_installed_is_unknown(self):
        self.assertEqual(send_patch_status("instagram-cli-that-does-not-exist"), PatchStatus.UNKNOWN)


class WarningTest(unittest.TestCase):
    def test_warns_when_the_patch_is_missing(self):
        install = FakeInstall(UNPATCHED)
        self.addCleanup(install.cleanup)
        with self.assertLogs(LOGGER, "WARNING") as logs:
            warn_if_send_patch_missing(str(install.executable))
        self.assertIn("WITHOUT our send fix", logs.output[0])
        self.assertIn("install.sh", logs.output[0])

    def test_warns_when_it_cannot_check(self):
        with self.assertLogs(LOGGER, "WARNING") as logs:
            warn_if_send_patch_missing("instagram-cli-that-does-not-exist")
        self.assertIn("Could not check", logs.output[0])

    def test_silent_when_the_patch_is_applied(self):
        install = FakeInstall(PATCHED)
        self.addCleanup(install.cleanup)
        with self.assertNoLogs(LOGGER):
            warn_if_send_patch_missing(str(install.executable))


class AdapterChecksOnStartTest(unittest.TestCase):
    def test_adapter_warns_on_creation(self):
        install = FakeInstall(UNPATCHED)
        self.addCleanup(install.cleanup)
        cli = InstagramCli(executable=str(install.executable), runner=FakeRunner())
        with self.assertLogs(LOGGER, "WARNING"):
            InstagramAdapter(cli)

    def test_check_can_be_turned_off(self):
        cli = InstagramCli(executable="instagram-cli-that-does-not-exist", runner=FakeRunner())
        with self.assertNoLogs(LOGGER):
            InstagramAdapter(cli, check_send_patch=False)


if __name__ == "__main__":
    unittest.main()

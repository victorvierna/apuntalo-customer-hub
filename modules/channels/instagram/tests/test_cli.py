import subprocess
import unittest

from modules.channels.instagram.cli import InstagramCli
from modules.channels.instagram.errors import (
    InstagramAuthError,
    InstagramCliError,
    InstagramCliNotFoundError,
    InstagramCliTimeoutError,
    InstagramFormatError,
)

from .helpers import FakeRunner


class BuildCommandTest(unittest.TestCase):
    def test_adds_json_output(self):
        cli = InstagramCli(runner=FakeRunner())
        self.assertEqual(
            cli.build_command(["inbox", "--limit=5"]),
            ["instagram-cli", "inbox", "--limit=5", "--output=json"],
        )

    def test_adds_account_when_configured(self):
        cli = InstagramCli(account="cuenta_prueba", runner=FakeRunner())
        self.assertEqual(cli.build_command(["inbox"])[-1], "--username=cuenta_prueba")

    def test_custom_executable(self):
        cli = InstagramCli(executable="/opt/bin/instagram-cli", runner=FakeRunner())
        self.assertEqual(cli.build_command(["inbox"])[0], "/opt/bin/instagram-cli")


class RunTest(unittest.TestCase):
    def test_returns_data_on_success(self):
        runner = FakeRunner.from_fixture("send_ok.json")
        data = InstagramCli(runner=runner).run(["send", "x"])
        self.assertEqual(data["messageId"], "30000000000000000000000000000000009")

    def test_never_uses_a_shell_and_sets_timeout(self):
        runner = FakeRunner.from_fixture("send_ok.json")
        InstagramCli(timeout=12, runner=runner).run(["send", "x"])
        kwargs = runner.kwargs[-1]
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["timeout"], 12)
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertIsInstance(runner.last_command, list)

    def test_no_session_is_an_auth_error(self):
        runner = FakeRunner.from_fixture("error_no_session.json")
        with self.assertRaisesRegex(InstagramAuthError, "Please login first"):
            InstagramCli(runner=runner).run(["inbox"])

    def test_other_errors_keep_the_message(self):
        runner = FakeRunner.from_fixture("error_no_thread.json")
        with self.assertRaises(InstagramCliError) as caught:
            InstagramCli(runner=runner).run(["read", "123"])
        self.assertNotIsInstance(caught.exception, InstagramAuthError)
        self.assertIn("No thread found", str(caught.exception))

    def test_challenge_is_an_auth_error(self):
        runner = FakeRunner(stdout='{"ok": false, "error": "challenge_required"}', returncode=1)
        with self.assertRaises(InstagramAuthError):
            InstagramCli(runner=runner).run(["inbox"])

    def test_not_installed(self):
        runner = FakeRunner(raises=FileNotFoundError())
        with self.assertRaises(InstagramCliNotFoundError):
            InstagramCli(runner=runner).run(["inbox"])

    def test_timeout(self):
        runner = FakeRunner(raises=subprocess.TimeoutExpired(cmd="instagram-cli", timeout=1))
        with self.assertRaises(InstagramCliTimeoutError):
            InstagramCli(runner=runner).run(["inbox"])

    def test_output_that_is_not_json(self):
        runner = FakeRunner(stdout="ERROR Raw mode is not supported", returncode=1, stderr="boom")
        with self.assertRaisesRegex(InstagramCliError, "did not return JSON.*boom"):
            InstagramCli(runner=runner).run(["inbox"])

    def test_json_without_ok_field(self):
        runner = FakeRunner(stdout='{"data": []}')
        with self.assertRaises(InstagramFormatError):
            InstagramCli(runner=runner).run(["inbox"])


if __name__ == "__main__":
    unittest.main()

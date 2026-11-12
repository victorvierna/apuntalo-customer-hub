"""The whole adapter (adapter + cli + mapper) against a fake instagram-cli."""

import tempfile
import unittest
from pathlib import Path

from modules.channels.instagram import (
    InstagramAdapter,
    InstagramCli,
    InstagramCliError,
    InstagramDeliveryError,
)
from shared.types.messages import ContentType, Direction

from .helpers import THREAD_ID, FakeRunner

SENT_ID = "30000000000000000000000000000000009"


def adapter_with(runner: FakeRunner, sleeps: list | None = None) -> InstagramAdapter:
    """Adapter on a fake instagram-cli. Never really sleeps; records the waits."""
    sleeps = [] if sleeps is None else sleeps
    return InstagramAdapter(InstagramCli(runner=runner), sleep=sleeps.append)


class ListConversationsTest(unittest.TestCase):
    def test_lists_conversations(self):
        runner = FakeRunner.from_fixture("inbox.json")
        conversations = adapter_with(runner).list_conversations(limit=5)
        self.assertEqual(runner.last_command[1:3], ["inbox", "--limit=5"])
        self.assertEqual(
            [c.external_id for c in conversations],
            [
                "340282366841710300000000000000000000001",
                "340282366841710300000000000000000000002",
            ],
        )

    def test_rejects_invalid_limit(self):
        adapter = adapter_with(FakeRunner())
        for limit in (0, -1, "5", True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                adapter.list_conversations(limit=limit)


class ReadMessagesTest(unittest.TestCase):
    def test_reads_and_translates_all_types(self):
        runner = FakeRunner.from_fixture("read_all_types.json")
        messages = adapter_with(runner).read_messages(THREAD_ID, limit=10)

        self.assertEqual(runner.last_command[1:4], ["read", THREAD_ID, "--limit=10"])
        self.assertNotIn("--mark-seen", runner.last_command)
        self.assertEqual(
            [m.content_type for m in messages],
            [
                ContentType.TEXT,
                ContentType.UNSUPPORTED,
                ContentType.UNSUPPORTED,
                ContentType.UNSUPPORTED,
                ContentType.MEDIA,
                ContentType.UNSUPPORTED,
                ContentType.REACTION,
                ContentType.TEXT,
            ],
        )
        self.assertEqual(messages[-1].direction, Direction.OUT)
        self.assertTrue(all(m.conversation_external_id == THREAD_ID for m in messages))


class SendTextTest(unittest.TestCase):
    def test_sends_and_returns_message_id(self):
        runner = FakeRunner.from_fixture("send_ok.json")
        message_id = adapter_with(runner).send_text(
            THREAD_ID, "Hola, ¿en qué te ayudo?", verify=False
        )
        self.assertEqual(message_id, SENT_ID)
        self.assertEqual(len(runner.calls), 1, "verify=False must not read the conversation")
        self.assertEqual(
            runner.last_command[1:4],
            ["send", THREAD_ID, "--text=Hola, ¿en qué te ayudo?"],
        )

    def test_text_starting_with_dash_stays_a_value(self):
        runner = FakeRunner.from_fixture("send_ok.json")
        adapter_with(runner).send_text(THREAD_ID, "-hola --mark-seen", verify=False)
        self.assertIn("--text=-hola --mark-seen", runner.last_command)

    def test_refuses_empty_text(self):
        runner = FakeRunner()
        with self.assertRaises(ValueError):
            adapter_with(runner).send_text(THREAD_ID, "   ")
        self.assertEqual(runner.calls, [])

    def test_unconfirmed_send_is_an_error(self):
        runner = FakeRunner(stdout='{"ok": true, "data": {"sent": false}}')
        with self.assertRaises(InstagramCliError):
            adapter_with(runner).send_text(THREAD_ID, "hola")


class DeliveryCheckTest(unittest.TestCase):
    """instagram-cli says "sent" even when Instagram silently drops the message."""

    def test_verifies_by_default_and_passes_when_message_appears(self):
        runner = FakeRunner.sequence("send_ok.json", "read_after_send.json")
        sleeps = []
        message_id = adapter_with(runner, sleeps).send_text(THREAD_ID, "Hola, ¿en qué te ayudo?")
        self.assertEqual(message_id, SENT_ID)
        self.assertEqual([c[1] for c in runner.calls], ["send", "read"])
        self.assertNotIn("--mark-seen", runner.last_command)
        self.assertEqual(len(sleeps), 1)

    def test_lost_message_raises_delivery_error_after_retrying(self):
        # The conversation never shows the sent message.
        runner = FakeRunner.sequence("send_ok.json", "read_all_types.json")
        sleeps = []
        with self.assertRaises(InstagramDeliveryError) as caught:
            adapter_with(runner, sleeps).send_text(THREAD_ID, "hola")
        self.assertEqual(caught.exception.message_id, SENT_ID)
        self.assertEqual([c[1] for c in runner.calls], ["send", "read", "read"])
        self.assertEqual(len(sleeps), 2)

    def test_failing_check_is_a_delivery_error_with_the_id(self):
        # Sent fine, but reading the conversation afterwards fails: the state is
        # unknown, so it must not look like a plain send failure (no resend).
        runner = FakeRunner.sequence("send_ok.json", "error_no_session.json")
        with self.assertRaises(InstagramDeliveryError) as caught:
            adapter_with(runner).send_text(THREAD_ID, "hola")
        self.assertEqual(caught.exception.message_id, SENT_ID)

    def test_delivery_error_is_an_instagram_cli_error(self):
        self.assertTrue(issubclass(InstagramDeliveryError, InstagramCliError))

    def test_is_delivered(self):
        adapter = adapter_with(FakeRunner.from_fixture("read_after_send.json"))
        self.assertTrue(adapter.is_delivered(THREAD_ID, SENT_ID))
        self.assertFalse(adapter.is_delivered(THREAD_ID, "30000000000000000000000000000000077"))


class ConversationIdSafetyTest(unittest.TestCase):
    """instagram-cli searches anything that is not a 20+ digit id by name and can
    start a conversation with someone else. The adapter must never pass one."""

    def test_rejects_anything_but_a_numeric_id(self):
        runner = FakeRunner()
        adapter = adapter_with(runner)
        for bad in ("cliente.prueba", "123", "", f"{THREAD_ID} ", "Cliente Prueba"):
            with self.subTest(conversation_id=bad):
                with self.assertRaises(ValueError):
                    adapter.send_text(bad, "hola")
                with self.assertRaises(ValueError):
                    adapter.read_messages(bad)
        self.assertEqual(runner.calls, [], "instagram-cli must not run with a bad id")


class DownloadMediaTest(unittest.TestCase):
    def test_downloads_to_absolute_path(self):
        runner = FakeRunner.from_fixture("download_ok.json")
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "media" / "30000000000000000000000000000000005"
            path = adapter_with(runner).download_media(
                THREAD_ID, "30000000000000000000000000000000005", destination
            )
            self.assertTrue(destination.parent.is_dir())
        self.assertEqual(path.suffix, ".jpg")
        self.assertIn(f"--download={destination.resolve()}", runner.last_command)
        self.assertIn("--message-id=30000000000000000000000000000000005", runner.last_command)

    def test_unconfirmed_download_is_an_error(self):
        runner = FakeRunner(stdout='{"ok": true, "data": {"downloaded": false}}')
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(InstagramCliError):
            adapter_with(runner).download_media(THREAD_ID, "1", Path(tmp) / "x")


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import UTC, datetime

from modules.handoff import POLICY, Handling, decide
from shared.types.messages import ChannelMessage, ContentType, Direction


def message(content_type: ContentType, direction: Direction = Direction.IN) -> ChannelMessage:
    return ChannelMessage(
        channel="test",
        external_id="1",
        conversation_external_id="1",
        sender_external_id="1",
        direction=direction,
        content_type=content_type,
        body="hola" if content_type is ContentType.TEXT else None,
        created_at=datetime(2026, 11, 12, tzinfo=UTC),
    )


class PolicyTest(unittest.TestCase):
    def test_every_content_type_has_a_rule(self):
        # A new ContentType without a rule would crash decide() at runtime.
        self.assertEqual(set(POLICY), set(ContentType))

    def test_text_goes_to_the_assistant(self):
        self.assertEqual(decide(message(ContentType.TEXT)), Handling.ASSISTANT)

    def test_content_the_assistant_cannot_read_goes_to_a_person(self):
        for content_type in (ContentType.MEDIA, ContentType.UNSUPPORTED):
            with self.subTest(content_type=content_type):
                self.assertEqual(decide(message(content_type)), Handling.HANDOFF)

    def test_reactions_are_only_stored(self):
        self.assertEqual(decide(message(ContentType.REACTION)), Handling.STORE_ONLY)

    def test_outgoing_messages_are_only_stored(self):
        for content_type in ContentType:
            with self.subTest(content_type=content_type):
                self.assertEqual(
                    decide(message(content_type, Direction.OUT)), Handling.STORE_ONLY
                )

    def test_policy_cannot_be_changed_at_runtime(self):
        with self.assertRaises(TypeError):
            POLICY[ContentType.TEXT] = Handling.HANDOFF


if __name__ == "__main__":
    unittest.main()

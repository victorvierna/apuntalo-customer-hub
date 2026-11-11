import unittest
from datetime import UTC, datetime

from modules.channels.instagram.errors import InstagramFormatError
from modules.channels.instagram.mapper import to_conversation, to_message
from shared.types.messages import ContentType, Direction

from .helpers import THREAD_ID, fixture


def messages_by_id():
    raw = fixture("read_all_types.json")["data"]["messages"]
    return {item["id"][-1]: to_message(item, THREAD_ID) for item in raw}


class ToMessageTest(unittest.TestCase):
    def setUp(self):
        self.messages = messages_by_id()

    def test_text_message(self):
        message = self.messages["1"]
        self.assertEqual(message.channel, "instagram")
        self.assertEqual(message.external_id, "30000000000000000000000000000000001")
        self.assertEqual(message.conversation_external_id, THREAD_ID)
        self.assertEqual(message.sender_external_id, "1000000001")
        self.assertEqual(message.direction, Direction.IN)
        self.assertEqual(message.content_type, ContentType.TEXT)
        self.assertEqual(message.body, "¿Cuánto cuesta el curso?")

    def test_timestamp_is_utc_aware(self):
        self.assertEqual(
            self.messages["1"].created_at,
            datetime(2026, 11, 11, 8, 14, 50, 694000, tzinfo=UTC),
        )

    def test_placeholders_are_unsupported_and_keep_their_description(self):
        expected = {
            "2": "[Unsupported Type: voice_media]",
            "3": "[Unsupported Type: xma_media_share]",
            "4": "[Instagram CLI successfully blocked a brainrot]",
            "7": "[Sent a ❤️]",
        }
        for key, body in expected.items():
            with self.subTest(body=body):
                self.assertEqual(self.messages[key].content_type, ContentType.UNSUPPORTED)
                self.assertEqual(self.messages[key].body, body)

    def test_photo_is_media_without_body(self):
        message = self.messages["5"]
        self.assertEqual(message.content_type, ContentType.MEDIA)
        self.assertIsNone(message.body)

    def test_link_without_text_gets_a_description(self):
        # instagram-cli leaves links out of the JSON: no text, no url.
        message = self.messages["6"]
        self.assertEqual(message.content_type, ContentType.UNSUPPORTED)
        self.assertEqual(message.body, "[link]")

    def test_outgoing_message(self):
        message = self.messages["8"]
        self.assertEqual(message.direction, Direction.OUT)
        self.assertEqual(message.sender_external_id, "1000000099")

    def test_unknown_item_type_is_unsupported(self):
        raw = self._raw(itemType="something_new")
        raw.pop("text")
        message = to_message(raw, THREAD_ID)
        self.assertEqual(message.content_type, ContentType.UNSUPPORTED)
        self.assertEqual(message.body, "[something_new]")

    def test_empty_text_is_text_with_empty_body(self):
        # instagram-cli sends "" when a text message has no text.
        message = to_message(self._raw(text=""), THREAD_ID)
        self.assertEqual(message.content_type, ContentType.TEXT)
        self.assertEqual(message.body, "")

    def test_missing_required_fields_raise(self):
        for key in ("id", "userId", "timestamp", "isOutgoing"):
            with self.subTest(missing=key):
                raw = self._raw()
                raw.pop(key)
                with self.assertRaises(InstagramFormatError):
                    to_message(raw, THREAD_ID)

    def test_invalid_values_raise(self):
        cases = {
            "isOutgoing as string": {"isOutgoing": "false"},
            "timestamp without timezone": {"timestamp": "2026-11-11T08:14:50"},
            "timestamp not a date": {"timestamp": "ayer"},
            "empty id": {"id": ""},
        }
        for name, change in cases.items():
            with self.subTest(name):
                with self.assertRaises(InstagramFormatError):
                    to_message(self._raw(**change), THREAD_ID)

    def test_not_an_object_raises(self):
        with self.assertRaises(InstagramFormatError):
            to_message(["not", "a", "dict"], THREAD_ID)

    @staticmethod
    def _raw(**changes):
        raw = dict(fixture("read_all_types.json")["data"]["messages"][0])
        raw.update(changes)
        return raw


class ToConversationTest(unittest.TestCase):
    def test_inbox_thread(self):
        conversation = to_conversation(fixture("inbox.json")["data"][0])
        self.assertEqual(conversation.channel, "instagram")
        self.assertEqual(conversation.external_id, "340282366841710300000000000000000000001")
        self.assertEqual(conversation.title, "Cliente Prueba")
        self.assertEqual(conversation.participants, ("cliente.prueba",))
        self.assertEqual(
            conversation.last_activity_at,
            datetime(2026, 11, 11, 8, 21, 23, 748000, tzinfo=UTC),
        )

    def test_invalid_users_raise(self):
        raw = dict(fixture("inbox.json")["data"][0], users="cliente.prueba")
        with self.assertRaises(InstagramFormatError):
            to_conversation(raw)

    def test_missing_id_raises(self):
        raw = dict(fixture("inbox.json")["data"][0])
        raw.pop("id")
        with self.assertRaises(InstagramFormatError):
            to_conversation(raw)


if __name__ == "__main__":
    unittest.main()

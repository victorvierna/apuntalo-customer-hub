import json
import unittest
from datetime import UTC, datetime

from shared.types.messages import ChannelConversation, ChannelMessage, ContentType, Direction
from shared.types.queue import decode_payload, encode_payload

CONVERSATION = ChannelConversation(
    channel="instagram",
    external_id="340282366841710300000000000000000000001",
    title="Cliente Prueba",
    participants=("cliente.prueba",),
    last_activity_at=datetime(2026, 11, 17, 10, 0, tzinfo=UTC),
)
MESSAGE = ChannelMessage(
    channel="instagram",
    external_id="30000000000000000000000000000000003",
    conversation_external_id=CONVERSATION.external_id,
    sender_external_id="900",
    direction=Direction.IN,
    content_type=ContentType.REACTION,
    body="❤️",
    created_at=datetime(2026, 11, 17, 10, 0, 0, 748_000, tzinfo=UTC),
)


class PayloadTest(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(decode_payload(encode_payload(CONVERSATION, MESSAGE)), (CONVERSATION, MESSAGE))

    def test_malformed_payload_raises(self):
        data = json.loads(encode_payload(CONVERSATION, MESSAGE))
        del data["message"]["direction"]
        with self.assertRaises(KeyError):
            decode_payload(json.dumps(data))

    def test_dates_without_timezone_are_rejected(self):
        data = json.loads(encode_payload(CONVERSATION, MESSAGE))
        data["message"]["created_at"] = "2026-11-17T10:00:00"
        with self.assertRaises(ValueError):
            decode_payload(json.dumps(data))


if __name__ == "__main__":
    unittest.main()

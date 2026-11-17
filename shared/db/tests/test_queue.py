import unittest
from datetime import timedelta

from shared.db.connection import to_db_time
from shared.db.queue import enqueue, pending_burst, ready_conversations, record_failure

from .helpers import T0, THREAD_ID, DatabaseTestCase, conversation, message


class QueueTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.account = self.add_account()

    def enqueue(self, msg, at=T0, **kwargs) -> bool:
        return enqueue(self.conn, self.account, conversation(), msg, to_db_time(at), **kwargs)

    def test_a_reread_message_is_not_queued_again(self):
        self.assertTrue(self.enqueue(message("m1")))
        self.assertFalse(self.enqueue(message("m1"), at=T0 + timedelta(seconds=20)))
        self.assertEqual(self.count("inbound_queue"), 1)

    def test_a_conversation_is_ready_after_the_burst_window(self):
        self.enqueue(message("m1"), at=T0)
        self.enqueue(message("m2"), at=T0 + timedelta(seconds=5))
        self.assertEqual(ready_conversations(self.conn, to_db_time(T0 + timedelta(seconds=4))), [])
        self.assertEqual(
            ready_conversations(self.conn, to_db_time(T0 + timedelta(seconds=5))),
            [(self.account, THREAD_ID)],
        )

    def test_pending_burst_decodes_the_payload(self):
        self.enqueue(message("m1", body="¿Cuánto cuesta?"), is_backfill=True)
        [item] = pending_burst(self.conn, self.account, THREAD_ID)
        self.assertEqual(item.message.body, "¿Cuánto cuesta?")
        self.assertEqual(item.conversation.participants, ("cliente.prueba",))
        self.assertTrue(item.is_backfill)

    def test_failures_are_retried_until_the_limit(self):
        self.enqueue(message("m1"))
        for attempt in (1, 2):
            record_failure(self.conn, self.account, THREAD_ID, "boom", to_db_time(T0), 3)
            row = self.row("SELECT status, attempts FROM inbound_queue")
            self.assertEqual((row["status"], row["attempts"]), ("pending", attempt))
        record_failure(self.conn, self.account, THREAD_ID, "boom", to_db_time(T0), 3)
        row = self.row("SELECT status, attempts, error, finished_at FROM inbound_queue")
        self.assertEqual((row["status"], row["attempts"], row["error"]), ("failed", 3, "boom"))
        self.assertIsNotNone(row["finished_at"])


if __name__ == "__main__":
    unittest.main()

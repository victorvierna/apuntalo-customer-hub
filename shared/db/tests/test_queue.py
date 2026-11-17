import unittest
from datetime import timedelta

from shared.db.connection import to_db_time
from shared.db.queue import (
    MAX_WAIT,
    QUIET_PERIOD,
    due_rechecks,
    enqueue,
    mark_checked,
    pending_burst,
    ready_conversations,
    record_failure,
)
from shared.types.messages import Direction

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

    def check(self, at, found_new_incoming=False):
        mark_checked(self.conn, self.account, THREAD_ID, to_db_time(at), found_new_incoming)

    def ready(self, at):
        return ready_conversations(self.conn, at) == [(self.account, THREAD_ID)]

    def test_a_burst_is_over_when_a_reread_after_the_quiet_period_finds_nothing(self):
        self.enqueue(message("m1"), at=T0)
        self.check(T0, found_new_incoming=True)
        self.assertFalse(self.ready(T0 + QUIET_PERIOD))  # no re-read yet

        self.check(T0 + QUIET_PERIOD - timedelta(seconds=1))  # too early
        self.assertFalse(self.ready(T0 + QUIET_PERIOD))

        self.check(T0 + QUIET_PERIOD)
        self.assertTrue(self.ready(T0 + QUIET_PERIOD))

    def test_a_new_message_found_by_the_reread_extends_the_burst(self):
        later = T0 + QUIET_PERIOD
        self.enqueue(message("m1"), at=T0)
        self.check(T0, found_new_incoming=True)
        self.enqueue(message("m2"), at=later)
        self.check(later, found_new_incoming=True)
        self.assertFalse(self.ready(later))
        self.check(later + QUIET_PERIOD)
        self.assertTrue(self.ready(later + QUIET_PERIOD))

    def test_without_rereads_the_burst_is_taken_after_the_max_wait(self):
        self.enqueue(message("m1"), at=T0)
        self.assertFalse(self.ready(T0 + MAX_WAIT - timedelta(seconds=1)))
        self.assertTrue(self.ready(T0 + MAX_WAIT))

    def test_history_and_outgoing_messages_do_not_wait(self):
        self.enqueue(message("m1"), is_backfill=True)
        self.enqueue(message("m2", direction=Direction.OUT))
        self.assertTrue(self.ready(T0))

    def test_reread_scheduling(self):
        self.check(T0, found_new_incoming=True)
        self.assertEqual(due_rechecks(self.conn, self.account, to_db_time(T0)), [])
        due = T0 + QUIET_PERIOD
        self.assertEqual(due_rechecks(self.conn, self.account, to_db_time(due)), [THREAD_ID])

        # An early read with nothing new (the normal pass) keeps the pending re-read.
        self.check(T0 + timedelta(seconds=5))
        self.assertEqual(due_rechecks(self.conn, self.account, to_db_time(due)), [THREAD_ID])

        # The re-read finds nothing new: done.
        self.check(due)
        self.assertEqual(due_rechecks(self.conn, self.account, to_db_time(due)), [])

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

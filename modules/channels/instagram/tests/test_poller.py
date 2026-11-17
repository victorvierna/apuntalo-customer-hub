"""The Instagram reader, with a fake adapter and a real SQLite file.

Every id, name and text is invented. Never put real customer data here.
"""

import unittest
from datetime import timedelta

from modules.channels.instagram.adapter import MessagePage
from modules.channels.instagram.errors import InstagramAuthError, InstagramCliError
from modules.channels.instagram.poller import backfill_flags, poll_once
from modules.gateway import run_once
from modules.gateway.worker import BURST_WINDOW
from shared.db.tests.helpers import T0, DatabaseTestCase, conversation, message
from shared.types.gateway import GatewayResult
from shared.types.messages import Direction

THREAD_A = "340282366841710300000000000000000000001"
THREAD_B = "340282366841710300000000000000000000002"


class FakeAdapter:
    """Answers like InstagramAdapter from what the test puts in ``threads``."""

    def __init__(self):
        self.threads = {}  # external_id -> (ChannelConversation, [ChannelMessage])
        self.failing = {}  # external_id -> exception raised by read_messages

    def add(self, thread_id, *messages, participants=("cliente.prueba",)):
        conv = conversation(thread_id=thread_id, participants=participants)
        self.threads[thread_id] = (conv, list(messages))

    def write(self, thread_id, *messages):
        self.threads[thread_id][1].extend(messages)

    def list_conversations(self, limit=20):
        return [conv for conv, _ in self.threads.values()][:limit]

    def read_messages(self, conversation_id, limit=20):
        return self.read_page(conversation_id, limit).messages

    def read_page(self, conversation_id, limit=20, cursor=None):
        if conversation_id in self.failing:
            raise self.failing[conversation_id]
        messages = self.threads[conversation_id][1]
        end = len(messages) if cursor is None else int(cursor)
        start = max(0, end - limit)
        return MessagePage(
            messages=messages[start:end],
            next_cursor=str(start) if start > 0 else None,
        )


def msg(external_id, minutes, direction=Direction.IN, thread_id=THREAD_A, body="hola"):
    return message(
        external_id,
        body=body,
        direction=direction,
        thread_id=thread_id,
        created_at=T0 + timedelta(minutes=minutes),
    )


class BackfillFlagsTest(unittest.TestCase):
    def test_the_first_sync_is_all_history(self):
        messages = [msg("m1", 0), msg("m2", 1, Direction.OUT), msg("m3", 2)]
        self.assertEqual(backfill_flags(messages, first_sync=True, known=False), [True] * 3)

    def test_everything_new_in_a_known_conversation_is_answered(self):
        messages = [msg("m1", 0), msg("m2", 1, Direction.OUT), msg("m3", 2)]
        self.assertEqual(backfill_flags(messages, first_sync=False, known=True), [False] * 3)

    def test_a_new_conversation_is_history_up_to_our_last_reply(self):
        messages = [msg("m1", 0), msg("m2", 1, Direction.OUT), msg("m3", 2), msg("m4", 3)]
        self.assertEqual(
            backfill_flags(messages, first_sync=False, known=False), [True, True, False, False]
        )

    def test_an_accepted_message_request_is_answered_entirely(self):
        messages = [msg("m1", 0), msg("m2", 1)]
        self.assertEqual(backfill_flags(messages, first_sync=False, known=False), [False, False])


class PollerTestCase(DatabaseTestCase):
    """An account, a fake adapter and helpers. Has no tests of its own."""

    def setUp(self):
        super().setUp()
        self.account = self.add_account()
        self.adapter = FakeAdapter()

    def poll(self, at=T0):
        return poll_once(self.conn, self.adapter, self.account, at)

    def queued(self):
        """``{message_external_id: is_backfill}`` of everything in the queue."""
        rows = self.conn.execute("SELECT message_external_id, is_backfill FROM inbound_queue")
        return {row[0]: bool(row[1]) for row in rows}


class PollerTest(PollerTestCase):
    def test_the_first_pass_queues_everything_as_history(self):
        self.adapter.add(THREAD_A, msg("a1", 0), msg("a2", 1, Direction.OUT), msg("a3", 2))
        self.adapter.add(THREAD_B, msg("b1", 0, thread_id=THREAD_B))

        result = self.poll()

        self.assertTrue(result.first_sync)
        self.assertEqual(result.conversations_read, 2)
        self.assertEqual(result.messages_queued, 4)
        self.assertEqual(self.queued(), {"a1": True, "a2": True, "a3": True, "b1": True})

    def test_a_reread_queues_nothing_and_a_new_message_is_answered(self):
        self.adapter.add(THREAD_A, msg("a1", 0))
        self.poll()

        self.assertEqual(self.poll(at=T0 + timedelta(seconds=20)).messages_queued, 0)

        self.adapter.write(THREAD_A, msg("a2", 5))
        result = self.poll(at=T0 + timedelta(seconds=40))
        self.assertFalse(result.first_sync)
        self.assertEqual(result.messages_queued, 1)
        self.assertEqual(self.queued(), {"a1": True, "a2": False})

    def test_a_conversation_seen_for_the_first_time_skips_what_we_already_answered(self):
        self.adapter.add(THREAD_A, msg("a1", 0))
        self.poll()

        # An older conversation shows up again because the contact wrote.
        self.adapter.add(
            THREAD_B,
            msg("b1", 0, thread_id=THREAD_B),
            msg("b2", 1, Direction.OUT, thread_id=THREAD_B),
            msg("b3", 60, thread_id=THREAD_B),
        )
        self.poll(at=T0 + timedelta(hours=1))

        queued = self.queued()
        self.assertEqual((queued["b1"], queued["b2"], queued["b3"]), (True, True, False))

    def test_the_account_stays_synced_after_the_queue_is_cleaned(self):
        self.adapter.add(THREAD_A, msg("a1", 0))
        self.poll()
        run_once(self.conn, T0 + BURST_WINDOW)
        self.conn.execute("DELETE FROM inbound_queue")

        self.adapter.write(THREAD_A, msg("a2", 5))
        result = self.poll(at=T0 + timedelta(minutes=10))

        self.assertFalse(result.first_sync)
        # a1 is queued again, still known: the gateway discards it as a duplicate.
        self.assertEqual(self.queued(), {"a1": False, "a2": False})

    def test_group_conversations_are_not_queued(self):
        self.adapter.add(THREAD_A, msg("a1", 0), participants=("uno", "dos"))
        result = self.poll()
        self.assertEqual(result.groups_skipped, 1)
        self.assertEqual(self.queued(), {})

    def test_a_conversation_that_fails_does_not_stop_the_others(self):
        self.adapter.add(THREAD_A, msg("a1", 0))
        self.adapter.add(THREAD_B, msg("b1", 0, thread_id=THREAD_B))
        self.adapter.failing[THREAD_A] = InstagramCliError("timeout")

        with self.assertLogs("modules.channels.instagram.poller", "ERROR"):
            result = self.poll()

        self.assertEqual(result.failed_conversations, [THREAD_A])
        self.assertEqual(self.queued(), {"b1": True})

    def test_an_expired_session_stops_the_pass(self):
        self.adapter.add(THREAD_A, msg("a1", 0))
        self.adapter.failing[THREAD_A] = InstagramAuthError("login_required")
        with self.assertRaises(InstagramAuthError):
            self.poll()


class ReaderAndGatewayTest(PollerTestCase):
    """The reader and the gateway together: history is stored, not answered."""

    def test_history_is_stored_as_context_and_only_the_new_message_is_answered(self):
        self.adapter.add(
            THREAD_A,
            msg("a1", 0, body="¿Cuánto cuesta el curso?"),
            msg("a2", 1, Direction.OUT, body="49 €"),
            msg("a3", 2, body="¡Gracias!"),
        )
        self.poll()
        self.assertEqual(run_once(self.conn, T0 + BURST_WINDOW), [])
        self.assertEqual(self.count("messages"), 3)

        self.adapter.write(THREAD_A, msg("a4", 60 * 24, body="¿Hay descuento?"))
        later = T0 + timedelta(days=1)
        self.poll(at=later)
        [decision] = run_once(self.conn, later + BURST_WINDOW)

        self.assertIs(decision.result, GatewayResult.ACCEPTED)
        self.assertEqual(len(decision.message_ids), 1)
        self.assertEqual(self.count("messages", "conversation_id = ?", (decision.conversation_id,)), 4)


class PagingTest(PollerTestCase):
    def test_a_long_gap_is_read_back_to_the_last_message_we_had(self):
        self.adapter.add(THREAD_A, msg("a0", 0))
        self.poll()
        # 25 messages arrived while the reader was down: more than one page.
        self.adapter.write(THREAD_A, *(msg(f"n{i}", i + 1) for i in range(25)))

        result = self.poll(at=T0 + timedelta(minutes=30))

        self.assertEqual(result.messages_queued, 25)
        self.assertEqual(result.gap_conversations, [])
        self.assertEqual(len(self.queued()), 26)

    def test_too_many_missed_messages_are_reported_as_a_gap(self):
        self.adapter.add(THREAD_A, msg("a0", 0))
        self.poll()
        self.adapter.write(THREAD_A, *(msg(f"n{i}", i + 1) for i in range(250)))

        result = self.poll(at=T0 + timedelta(hours=5))

        self.assertEqual(result.gap_conversations, [THREAD_A])
        self.assertEqual(result.messages_queued, 200)
        self.assertEqual(len(self.queued()), 201)  # a0 from the first pass, plus 200 newest

    def test_a_full_inbox_is_reported(self):
        for i in range(10):
            self.adapter.add(f"thread-{i}", msg(f"m{i}", i, thread_id=f"thread-{i}"))

        result = self.poll()

        self.assertTrue(result.inbox_full)

    def test_a_short_inbox_is_not_reported(self):
        self.adapter.add(THREAD_A, msg("a1", 0))

        self.assertFalse(self.poll().inbox_full)


if __name__ == "__main__":
    unittest.main()

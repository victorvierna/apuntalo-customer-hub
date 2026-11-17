"""The whole gateway, from the queue to the processing run, on a real SQLite file."""

import json
import unittest
from datetime import timedelta
from unittest import mock

from modules.gateway import run_once
from modules.gateway.ingest import SKIP_GROUP, SKIP_UNKNOWN_CONTACT
from modules.gateway.worker import BURST_WINDOW, MAX_ATTEMPTS
from shared.db.connection import to_db_time
from shared.db.queue import enqueue
from shared.db.runs import unfinished_accepted_runs
from shared.db.tests.helpers import T0, DatabaseTestCase, conversation, message
from shared.types.gateway import GatewayResult
from shared.types.messages import ContentType, Direction

LATER = T0 + BURST_WINDOW


class GatewayTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.account = self.add_account()

    def enqueue(self, *messages, conv=None, account=None, at=T0, is_backfill=False):
        for msg in messages:
            enqueue(
                self.conn,
                account or self.account,
                conv or conversation(),
                msg,
                to_db_time(at),
                is_backfill=is_backfill,
            )

    def run_gateway(self, now=LATER):
        return run_once(self.conn, now)

    def queue_statuses(self):
        return [row[0] for row in self.conn.execute("SELECT status FROM inbound_queue ORDER BY id")]

    def run_row(self, run_id):
        return self.row("SELECT * FROM processing_runs WHERE id = ?", (run_id,))

    def add_block(self, person_id, status="active", source="human"):
        self.conn.execute(
            """
            INSERT INTO blocks (person_id, source, status, run_id, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                person_id,
                source,
                status,
                None if source != "router" else self.any_run_id(),
                "motivo de prueba",
                to_db_time(T0),
            ),
        )

    def any_run_id(self):
        return self.row("SELECT id FROM processing_runs LIMIT 1")[0]

    def first_person(self, external_id="900"):
        """Processes a first message from this sender and returns their person id."""
        self.enqueue(message(f"first-{external_id}", sender=external_id), at=T0 - timedelta(hours=1))
        [decision] = self.run_gateway(T0 - timedelta(hours=1) + BURST_WINDOW)
        return decision.person_id

    # Normal flow

    def test_first_message_is_accepted_and_waits_for_an_answer(self):
        self.enqueue(message("m1", body="¿Cuánto cuesta el curso?"))
        [decision] = self.run_gateway()

        self.assertEqual(decision.result, GatewayResult.ACCEPTED)
        self.assertTrue(decision.is_new_person)
        self.assertTrue(decision.is_new_identity)
        run = self.run_row(decision.run_id)
        self.assertIsNone(run["finished_at"])
        self.assertIsNone(run["outcome"])
        self.assertEqual(unfinished_accepted_runs(self.conn), [decision.run_id])
        self.assertEqual(self.queue_statuses(), ["done"])
        self.assertEqual(self.count("messages", "author = 'contact'"), 1)
        self.assertEqual(self.row("SELECT username FROM contacts")[0], "cliente.prueba")

    def test_a_burst_is_one_run(self):
        self.enqueue(
            message("m1", body="hola", created_at=T0),
            message("m2", body="una duda", created_at=T0 + timedelta(seconds=2)),
            message("m3", body="¿cuánto cuesta?", created_at=T0 + timedelta(seconds=4)),
        )
        [decision] = self.run_gateway()
        self.assertEqual(len(decision.message_ids), 3)
        self.assertEqual(self.count("processing_runs"), 1)
        self.assertEqual(self.count("run_messages", "run_id = ?", (decision.run_id,)), 3)
        bodies = [
            row[0]
            for row in self.conn.execute(
                "SELECT body FROM messages WHERE id IN (?, ?, ?) ORDER BY id", decision.message_ids
            )
        ]
        self.assertEqual(bodies, ["hola", "una duda", "¿cuánto cuesta?"])

    def test_waits_for_the_burst_window(self):
        self.enqueue(message("m1"), at=T0)
        self.assertEqual(self.run_gateway(now=T0 + BURST_WINDOW - timedelta(seconds=1)), [])
        self.assertEqual(self.queue_statuses(), ["pending"])
        self.assertEqual(len(self.run_gateway()), 1)

    def test_known_person_writing_again(self):
        person_id = self.first_person()
        self.enqueue(message("m2"))
        [decision] = self.run_gateway()
        self.assertEqual(decision.person_id, person_id)
        self.assertFalse(decision.is_new_person)
        self.assertFalse(decision.is_new_identity)

    def test_same_username_from_another_account_is_the_same_person(self):
        person_id = self.first_person("900")
        other_account = self.add_account("apuntalo_b", "222")
        other_thread = "340282366841710300000000000000000000099"
        self.enqueue(
            message("m2", sender="901", thread_id=other_thread),
            conv=conversation(thread_id=other_thread),
            account=other_account,
        )
        [decision] = self.run_gateway()
        self.assertEqual(decision.person_id, person_id)
        self.assertFalse(decision.is_new_person)
        self.assertTrue(decision.is_new_identity)

    # Things that are stored but not processed

    def test_a_message_already_stored_is_not_processed_again(self):
        # E.g. its queue row was cleaned up and the reader queued it again.
        self.first_person()
        self.conn.execute("DELETE FROM inbound_queue")
        self.enqueue(message("first-900"))
        self.assertEqual(self.run_gateway(), [])
        self.assertEqual(self.count("processing_runs"), 1)
        self.assertEqual(self.queue_statuses(), ["done"])

    def test_history_is_stored_but_not_answered(self):
        self.enqueue(message("m1"), message("m2"), is_backfill=True)
        self.assertEqual(self.run_gateway(), [])
        self.assertEqual(self.count("messages"), 2)
        self.assertEqual(self.count("people"), 1)
        self.assertEqual(self.count("processing_runs"), 0)

    def test_outgoing_message_in_a_known_conversation_is_stored(self):
        self.first_person()
        self.enqueue(message("o1", body="Te escribo desde la app", direction=Direction.OUT))
        self.assertEqual(self.run_gateway(), [])
        row = self.row("SELECT author, delivery_status FROM messages WHERE external_id = 'o1'")
        self.assertEqual((row["author"], row["delivery_status"]), ("human", "sent"))
        self.assertEqual(self.count("processing_runs"), 1)

    def test_outgoing_message_to_an_unknown_person_is_skipped(self):
        self.enqueue(message("o1", direction=Direction.OUT))
        self.assertEqual(self.run_gateway(), [])
        self.assertEqual(self.count("conversations"), 0)
        row = self.row("SELECT status, error FROM inbound_queue")
        self.assertEqual((row["status"], row["error"]), ("done", SKIP_UNKNOWN_CONTACT))

    def test_group_conversations_are_skipped(self):
        self.enqueue(message("m1"), conv=conversation(participants=("ana", "luis")))
        self.assertEqual(self.run_gateway(), [])
        self.assertEqual(self.count("messages"), 0)
        self.assertEqual(self.row("SELECT error FROM inbound_queue")[0], SKIP_GROUP)

    # Checks

    def test_blocked_person_is_not_answered(self):
        person_id = self.first_person()
        self.add_block(person_id)
        self.enqueue(message("m2"))
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.BLOCKED_CONTACT)
        run = self.run_row(decision.run_id)
        self.assertEqual(run["outcome"], "stored_only")
        self.assertIsNotNone(run["finished_at"])
        self.assertEqual(self.count("messages", "external_id = 'm2'"), 1)

    def test_a_block_from_another_account_counts(self):
        # Blocked in account A, writes to account B with another identity.
        person_id = self.first_person("900")
        self.add_block(person_id)
        other_account = self.add_account("apuntalo_b", "222")
        other_thread = "340282366841710300000000000000000000099"
        self.enqueue(
            message("m2", sender="901", thread_id=other_thread),
            conv=conversation(thread_id=other_thread),
            account=other_account,
        )
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.BLOCKED_CONTACT)

    def test_a_router_proposal_does_not_block(self):
        person_id = self.first_person()
        self.add_block(person_id, status="proposed", source="router")
        self.enqueue(message("m2"))
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.ACCEPTED)

    def test_conversation_handled_by_a_person(self):
        self.first_person()
        self.conn.execute("UPDATE conversations SET status = 'waiting_human'")
        self.enqueue(message("m2"))
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.HUMAN_OWNED)
        self.assertEqual(self.run_row(decision.run_id)["outcome"], "stored_only")

    def test_a_closed_conversation_is_reopened(self):
        self.first_person()
        self.conn.execute("UPDATE conversations SET status = 'closed'")
        self.enqueue(message("m2"))
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.ACCEPTED)
        self.assertEqual(self.row("SELECT status FROM conversations")[0], "bot")

    def test_photo_is_handed_off(self):
        self.enqueue(message("m1", body=None, content_type=ContentType.IMAGE))
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.UNSUPPORTED_CONTENT)
        self.assertEqual(self.run_row(decision.run_id)["outcome"], "handed_off")
        handoff = self.row("SELECT run_id, reason, status FROM handoffs")
        self.assertEqual(
            (handoff["run_id"], handoff["reason"], handoff["status"]),
            (decision.run_id, "unsupported_content", "pending"),
        )
        self.assertEqual(self.row("SELECT status FROM conversations")[0], "waiting_human")

    def test_text_with_a_photo_is_handed_off(self):
        self.enqueue(
            message("m1", body="¿Esto entra en el curso?"),
            message("m2", body=None, content_type=ContentType.IMAGE),
        )
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.UNSUPPORTED_CONTENT)

    def test_a_reaction_is_only_stored(self):
        self.enqueue(message("m1", body="❤️", content_type=ContentType.REACTION))
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.STORE_ONLY)
        self.assertEqual(self.run_row(decision.run_id)["outcome"], "stored_only")

    def test_text_with_a_reaction_is_accepted(self):
        self.enqueue(
            message("m1", body="gracias"),
            message("m2", body="❤️", content_type=ContentType.REACTION),
        )
        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.ACCEPTED)

    # Failures

    def test_a_crash_loses_nothing(self):
        # The crash happens after the messages are stored: everything is
        # rolled back, so the retry sees them as new and answers them.
        self.enqueue(message("m1"))
        with self.assertLogs("modules.gateway.worker", "ERROR"):
            with mock.patch("modules.gateway.pipeline.create_run", side_effect=RuntimeError("crash")):
                self.assertEqual(self.run_gateway(), [])
        self.assertEqual(self.count("messages"), 0)
        self.assertEqual(self.queue_statuses(), ["pending"])

        [decision] = self.run_gateway()
        self.assertEqual(decision.result, GatewayResult.ACCEPTED)
        self.assertEqual(unfinished_accepted_runs(self.conn), [decision.run_id])

    def test_a_broken_burst_fails_without_stopping_the_others(self):
        other_thread = "340282366841710300000000000000000000099"
        self.enqueue(message("m1"))
        self.enqueue(message("m2", sender="901", thread_id=other_thread), conv=conversation(thread_id=other_thread))
        broken = json.loads(self.row("SELECT payload FROM inbound_queue WHERE id = 1")[0])
        del broken["message"]["direction"]
        self.conn.execute("UPDATE inbound_queue SET payload = ? WHERE id = 1", (json.dumps(broken),))

        with self.assertLogs("modules.gateway.worker", "ERROR"):
            decisions = self.run_gateway()
        self.assertEqual(len(decisions), 1)

        with self.assertLogs("modules.gateway.worker", "ERROR"):
            for _ in range(MAX_ATTEMPTS - 1):
                self.run_gateway()
        row = self.row("SELECT status, attempts, error FROM inbound_queue WHERE id = 1")
        self.assertEqual((row["status"], row["attempts"]), ("failed", MAX_ATTEMPTS))
        self.assertIn("KeyError", row["error"])


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import UTC, datetime, timedelta, timezone

from shared.db.connection import to_db_time, transaction

from .helpers import DatabaseTestCase


class ToDbTimeTest(unittest.TestCase):
    def test_always_utc_with_milliseconds(self):
        madrid = timezone(timedelta(hours=1))
        self.assertEqual(
            to_db_time(datetime(2026, 11, 17, 11, 0, 0, tzinfo=madrid)), "2026-11-17T10:00:00.000Z"
        )
        self.assertEqual(
            to_db_time(datetime(2026, 11, 17, 10, 0, 0, 748_900, tzinfo=UTC)),
            "2026-11-17T10:00:00.748Z",
        )

    def test_rejects_dates_without_timezone(self):
        with self.assertRaises(ValueError):
            to_db_time(datetime(2026, 11, 17))


class TransactionTest(DatabaseTestCase):
    def test_nothing_is_written_if_something_fails(self):
        with self.assertRaises(RuntimeError):
            with transaction(self.conn):
                self.add_account()
                raise RuntimeError("boom")
        self.assertEqual(self.count("channel_accounts"), 0)

    def test_foreign_keys_are_enforced(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()

import unittest

from modules.gateway.identity import normalize_username, resolve_identity
from shared.db.connection import to_db_time
from shared.db.tests.helpers import T0, DatabaseTestCase

NOW = to_db_time(T0)


class NormalizeUsernameTest(unittest.TestCase):
    def test_without_at_and_lowercase(self):
        self.assertEqual(normalize_username(" @Maria.G "), "maria.g")

    def test_empty_is_none(self):
        self.assertIsNone(normalize_username("@"))
        self.assertIsNone(normalize_username(None))


class ResolveIdentityTest(DatabaseTestCase):
    def resolve(self, external_id, username, channel="instagram"):
        return resolve_identity(self.conn, channel, external_id, username, "María", NOW)

    def test_first_time_creates_person_and_identity(self):
        identity = self.resolve("900", "maria.g")
        self.assertTrue(identity.is_new_person)
        self.assertTrue(identity.is_new_identity)
        self.assertEqual(self.count("people"), 1)

    def test_known_identity(self):
        first = self.resolve("900", "maria.g")
        again = self.resolve("900", "maria.g")
        self.assertEqual(again.contact_id, first.contact_id)
        self.assertFalse(again.is_new_person)
        self.assertFalse(again.is_new_identity)

    def test_same_username_links_to_the_same_person(self):
        first = self.resolve("900", "maria.g")
        other = self.resolve("901", "@Maria.G")
        self.assertEqual(other.person_id, first.person_id)
        self.assertNotEqual(other.contact_id, first.contact_id)
        self.assertFalse(other.is_new_person)
        self.assertTrue(other.is_new_identity)

    def test_same_username_in_another_channel_is_another_person(self):
        first = self.resolve("900", "maria.g")
        other = self.resolve("900", "maria.g", channel="whatsapp")
        self.assertNotEqual(other.person_id, first.person_id)
        self.assertTrue(other.is_new_person)

    def test_without_username_it_is_a_new_person(self):
        self.resolve("900", None)
        self.assertTrue(self.resolve("901", None).is_new_person)

    def test_a_changed_username_is_updated(self):
        identity = self.resolve("900", "maria.g")
        self.resolve("900", "maria.nueva")
        self.assertEqual(
            self.row("SELECT username FROM contacts WHERE id = ?", (identity.contact_id,))[0],
            "maria.nueva",
        )


if __name__ == "__main__":
    unittest.main()

"""Who is writing, and is it the first time? (``gateway.md`` section 5)."""

import sqlite3
from dataclasses import dataclass

from shared.db.contacts import (
    create_contact,
    create_person,
    find_contact,
    find_person_by_username,
    update_username,
)


@dataclass(frozen=True, slots=True)
class Identity:
    contact_id: int
    person_id: int
    is_new_person: bool
    is_new_identity: bool


def normalize_username(raw: str | None) -> str | None:
    """Without ``@`` and lowercase, as ``contacts.username`` requires."""
    if raw is None:
        return None
    username = raw.strip().lstrip("@").lower()
    return username or None


def resolve_identity(
    conn: sqlite3.Connection,
    channel: str,
    external_id: str,
    username: str | None,
    display_name: str | None,
    now: str,
) -> Identity:
    """Finds or creates the identity and its person.

    A new identity joins the person that already has the same username in the
    same channel; otherwise it is a new person. Different channels are never
    linked here: a person does it from the dashboard.
    """
    username = normalize_username(username)

    contact = find_contact(conn, channel, external_id)
    if contact is not None:
        # The username can change in the channel; keep the current one.
        if username is not None and username != contact["username"]:
            update_username(conn, contact["id"], username)
        return Identity(contact["id"], contact["person_id"], False, False)

    person_id = find_person_by_username(conn, channel, username) if username else None
    is_new_person = person_id is None
    if person_id is None:
        person_id = create_person(conn, display_name, now)
    contact_id = create_contact(conn, person_id, channel, external_id, username, display_name, now)
    return Identity(contact_id, person_id, is_new_person, True)

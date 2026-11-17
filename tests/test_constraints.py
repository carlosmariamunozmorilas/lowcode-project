"""Session 5 lab: every kind of database rule rejects bad data.

One test per kind of rule the lab asks for: a duplicate (UNIQUE), a value a
CHECK forbids, a missing required field (NOT NULL), a row pointing at nothing
(FOREIGN KEY), the delete rule (RESTRICT), and data surviving a reopen. The
append-only triggers and the cross-table CHECKs are in test_schema.py.

All of it runs on a temporary database (the `conn` fixture), never the demo one.
"""

import sqlite3

import pytest

import db
from conftest import CONSULTANT, LUNA, build

CLIENT_COLUMNS = """INSERT INTO clients (name, sector, products, audience, main_channels,
    avg_order_value_eur, contribution_margin, purchase_frequency, monthly_budget_eur,
    roi_target, business_model) VALUES (?, 'Toys', 'Kites', 'Parents', 'Meta', ?, ?, ?, 1000,
    0.2, 'dtc')"""


def add_client(conn, name="Kite Shop", aov=40, margin=0.4, frequency="occasional"):
    return conn.execute(CLIENT_COLUMNS, (name, aov, margin, frequency)).lastrowid


def add_action(conn, client_id=LUNA, title="Free shipping test", status="submitted",
               window_start=None, window_end=None):
    return conn.execute(
        """INSERT INTO actions (client_id, discipline, title, benefit_type, requester_id,
               status, window_start, window_end)
           VALUES (?, 'ecommerce', ?, 'contribution', ?, ?, ?, ?)""",
        (client_id, title, CONSULTANT, status, window_start, window_end)).lastrowid


# UNIQUE -------------------------------------------------------------------------

def test_a_second_client_with_the_same_name_is_rejected(conn):
    add_client(conn)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        add_client(conn)


def test_a_second_user_with_the_same_email_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute("""INSERT INTO users (email, full_name, password_hash)
                        VALUES ('user4@test.example', 'Copy', 'x')""")


# CHECK --------------------------------------------------------------------------

@pytest.mark.parametrize("aov, margin, frequency", [
    (0, 0.4, "occasional"),          # an average order must be above zero
    (40, 1.5, "occasional"),         # a margin is a share: above 0, at most 1
    (40, 0.4, "weekly"),             # only rare / occasional / monthly
])
def test_client_values_outside_the_rules_are_rejected(conn, aov, margin, frequency):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        add_client(conn, aov=aov, margin=margin, frequency=frequency)


def test_an_unknown_action_status_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        add_action(conn, status="finished")


def test_a_window_that_ends_before_it_starts_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        add_action(conn, window_start="2026-11-10", window_end="2026-11-01")


# NOT NULL -----------------------------------------------------------------------

def test_an_action_without_a_title_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError, match="NOT NULL"):
        add_action(conn, title=None)


# FOREIGN KEY --------------------------------------------------------------------

def test_an_action_for_a_store_that_does_not_exist_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        add_action(conn, client_id=999)


def test_without_the_pragma_the_same_orphan_gets_in(tmp_path, password_hash):
    """Why db.connect() switches foreign keys on: SQLite's default lets it in."""
    path = tmp_path / "plain.db"
    built = db.connect(str(path), must_exist=False)
    build(built, password_hash)
    built.close()
    plain = sqlite3.connect(path)                     # no PRAGMA foreign_keys = ON
    add_action(plain, client_id=999)                  # accepted: an orphan
    orphans = plain.execute("PRAGMA foreign_key_check").fetchall()
    plain.close()
    assert len(orphans) == 1


# The delete rule: RESTRICT --------------------------------------------------------

def test_a_store_with_actions_cannot_be_deleted(conn):
    add_action(conn)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute("DELETE FROM clients WHERE id = ?", (LUNA,))
    assert conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 1


def test_a_store_is_deactivated_instead(conn):
    add_action(conn)
    conn.execute("UPDATE clients SET is_active = 0 WHERE id = ?", (LUNA,))
    assert conn.execute("SELECT is_active FROM clients WHERE id = ?", (LUNA,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 1


# Persistence ----------------------------------------------------------------------

def test_data_survives_closing_and_reopening_the_file(tmp_path, password_hash):
    path = tmp_path / "persist.db"
    first = db.connect(str(path), must_exist=False)
    build(first, password_hash)
    add_client(first, name="Persistent Store")
    first.commit()
    first.close()

    reopened = db.connect(str(path))
    row = reopened.execute("SELECT name FROM clients WHERE name = 'Persistent Store'").fetchone()
    reopened.close()
    assert row is not None

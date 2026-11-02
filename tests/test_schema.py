"""What the schema itself refuses: spec v2 §11 tests 16, 23, 24."""

import sqlite3

import pytest

from conftest import CONSULTANT, LEAD_A, LUNA, add_action


def test_16_history_and_months_refuse_update_and_delete(conn):
    action = add_action(conn)
    conn.execute("""INSERT INTO action_history (action_id, to_status, actor_id)
                    VALUES (?, 'submitted', ?)""", (action, CONSULTANT))
    for statement in ("UPDATE action_history SET note = 'changed'", "DELETE FROM action_history"):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute(statement)
    conn.execute("""INSERT INTO components (id, client_id, name, discipline, lifecycle_stage,
                        benefit_type, measurement, started_on)
                    VALUES (1, ?, 'C', 'automations', 'conversion', 'contribution',
                            'holdout_kept', '2026-07-01')""", (LUNA,))
    conn.execute("""INSERT INTO component_months (component_id, client_id, month, recorded_by)
                    VALUES (1, ?, '2026-08', ?)""", (LUNA, CONSULTANT))
    for statement in ("UPDATE component_months SET operating_cost_eur = 1",
                      "DELETE FROM component_months"):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute(statement)


@pytest.mark.parametrize("is_service, hashed, automation", [
    (0, None, None),               # a person without a password
    (1, "hash", "shop_intake_2"),  # an automation with one
    (1, None, None),               # an automation without a name
    (0, "hash", "named"),          # a person with an automation name
])
def test_23_schema_refuses_mismatched_accounts(conn, is_service, hashed, automation):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("""INSERT INTO users (email, full_name, password_hash, is_service,
                            automation_name) VALUES ('x@test.example', 'X', ?, ?, ?)""",
                     (hashed, is_service, automation))


def test_24_foreign_keys_on_and_nothing_is_deleted(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    add_action(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM clients WHERE id = ?", (LUNA,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM users WHERE id = ?", (CONSULTANT,))


def test_reviewer_is_never_requester_or_owner_in_the_schema(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_action(conn, owner_id=LEAD_A, reviewer_id=LEAD_A)


def test_comparison_must_match_benefit_type_in_the_schema(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_action(conn, benefit_type="avoided_cost", comparison="holdout")


def test_72_plan_templates_loaded_with_valid_tags(conn):
    assert conn.execute("SELECT COUNT(*) FROM plan_templates").fetchone()[0] == 72
    assert conn.execute("SELECT COUNT(*) FROM plan_templates WHERE featured = 1").fetchone()[0] == 6
    featured = {r[0] for r in conn.execute("SELECT id FROM plan_templates WHERE featured = 1")}
    assert featured == {3, 20, 30, 43, 50, 65}

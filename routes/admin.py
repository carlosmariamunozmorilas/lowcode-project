"""Set-up for agency operations: clients, people, roles and assignments.

Admin may read every client and set things up, but has no sign-off bypass and
never closes an action.
"""

import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from auth import role_required
from db import get_db, transaction

bp = Blueprint("admin", __name__, url_prefix="/admin")

PERSON_ROLES = ("consultant", "lead", "admin")
CLIENT_TEXT = ("name", "sector", "products", "audience", "main_channels",
               "purchase_frequency", "business_model")
CLIENT_NUMBERS = ("avg_order_value_eur", "contribution_margin", "monthly_budget_eur",
                  "roi_target", "hourly_rate_eur")


@bp.route("/clients", methods=["GET", "POST"])
@role_required("admin")
def clients():
    conn = get_db()
    if request.method == "POST":
        try:
            values = {k: request.form.get(k, "").strip() for k in CLIENT_TEXT}
            for k in CLIENT_NUMBERS:
                values[k] = float(request.form.get(k, ""))
            with transaction(conn):
                conn.execute(
                    f"INSERT INTO clients ({', '.join(values)}) "
                    f"VALUES ({', '.join('?' for _ in values)})", tuple(values.values()))
        except (ValueError, sqlite3.IntegrityError) as error:
            flash(f"Not saved: {error}", "error")
        else:
            flash("Client created.", "success")
        return redirect(url_for("admin.clients"))
    rows = conn.execute("SELECT * FROM clients ORDER BY is_active DESC, name").fetchall()
    return render_template("admin_clients.html", clients=rows)


@bp.route("/clients/<int:client_id>/active", methods=["POST"])
@role_required("admin")
def client_active(client_id):
    """Deactivate or reactivate: a client is never deleted."""
    active = 1 if request.form.get("active") == "1" else 0
    conn = get_db()
    with transaction(conn):
        conn.execute("UPDATE clients SET is_active = ? WHERE id = ?", (active, client_id))
    flash("Client updated.", "success")
    return redirect(url_for("admin.clients"))


@bp.route("/users", methods=["GET", "POST"])
@role_required("admin")
def users():
    conn = get_db()
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        roles = [r for r in request.form.getlist("roles") if r in PERSON_ROLES]
        client_ids = [int(c) for c in request.form.getlist("clients") if c.isdigit()]
        if not email or not name or len(password) < 12 or not roles:
            flash("Not saved: email, name, at least one role and a password of 12 or more "
                  "characters are needed.", "error")
            return redirect(url_for("admin.users"))
        try:
            with transaction(conn):
                cur = conn.execute(
                    "INSERT INTO users (email, full_name, password_hash) VALUES (?, ?, ?)",
                    (email, name, generate_password_hash(password)))
                for role in roles:
                    conn.execute("INSERT INTO user_roles (user_id, role) VALUES (?, ?)",
                                 (cur.lastrowid, role))
                for client_id in client_ids:
                    conn.execute(
                        "INSERT INTO client_assignments (user_id, client_id) VALUES (?, ?)",
                        (cur.lastrowid, client_id))
        except sqlite3.IntegrityError as error:
            flash(f"Not saved: {error}", "error")
        else:
            flash("Person added.", "success")
        return redirect(url_for("admin.users"))
    people = conn.execute(
        """SELECT u.*, GROUP_CONCAT(DISTINCT r.role) AS roles,
                  (SELECT GROUP_CONCAT(c.name, ', ') FROM client_assignments a
                   JOIN clients c ON c.id = a.client_id WHERE a.user_id = u.id) AS client_names
           FROM users u LEFT JOIN user_roles r ON r.user_id = u.id
           GROUP BY u.id ORDER BY u.is_service, u.full_name""").fetchall()
    clients = conn.execute("SELECT id, name FROM clients WHERE is_active = 1 ORDER BY name").fetchall()
    return render_template("admin_users.html", people=people, clients=clients,
                           roles=PERSON_ROLES)

"""Sign-in, sessions, roles, client access and CSRF protection.

Access is enforced here, in the functions that load data, not by hiding links:
a consultant who changes an id in a URL gets 404, not another client's data
(spec v2 §5, test 13).
"""

import functools
import hmac
import secrets
from datetime import date

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash

import lifecycle
from db import get_db

bp = Blueprint("auth", __name__)


def today() -> date:
    """The app's 'today'; tests can fix it with the TODAY setting."""
    value = current_app.config.get("TODAY")
    return date.fromisoformat(value) if value else date.today()


def init_app(app) -> None:
    app.register_blueprint(bp)
    app.before_request(load_user)
    app.before_request(check_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token


def load_user() -> None:
    g.user = None
    g.roles = frozenset()
    user_id = session.get("user_id")
    if user_id is None:
        return
    user = get_db().execute(
        "SELECT * FROM users WHERE id = ? AND is_active = 1 AND is_service = 0", (user_id,)
    ).fetchone()
    if user is None:
        session.clear()
        return
    g.user = user
    g.roles = frozenset(r["role"] for r in get_db().execute(
        "SELECT role FROM user_roles WHERE user_id = ?", (user_id,)))


def actor() -> lifecycle.User:
    return lifecycle.User(g.user["id"], g.roles)


# --- CSRF ------------------------------------------------------------------------

def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def check_csrf() -> None:
    """Every form POST carries the session's token; the signed API is exempt."""
    if request.method != "POST" or request.path.startswith("/api/"):
        return
    sent = request.form.get("csrf_token", "")
    expected = session.get("csrf", "")
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400, "The form expired or did not come from this app. Reload and try again.")


# --- decorators and access ---------------------------------------------------------

def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @functools.wraps(view)
        @login_required
        def wrapped(**kwargs):
            if not g.roles & set(roles):
                abort(403, f"This page needs the role: {' or '.join(roles)}.")
            return view(**kwargs)
        return wrapped
    return decorator


def assigned_client_ids() -> set[int]:
    rows = get_db().execute(
        "SELECT client_id FROM client_assignments WHERE user_id = ?", (g.user["id"],))
    return {r["client_id"] for r in rows}


def get_client(client_id: int, *, write: bool = False):
    """A client the signed-in user may see — or 404, never another client's data.

    Admin may read every client; only people assigned to a client may change
    its data.
    """
    client = get_db().execute(
        "SELECT * FROM clients WHERE id = ? AND is_active = 1", (client_id,)).fetchone()
    if client is None:
        abort(404)
    if client_id in assigned_client_ids():
        return client
    if not write and "admin" in g.roles:
        return client
    abort(404)


def eligible_lead_ids(client_id: int) -> frozenset[int]:
    """Active leads assigned to the client: the people who may review its actions."""
    rows = get_db().execute(
        """SELECT u.id FROM users u
           JOIN user_roles r ON r.user_id = u.id AND r.role = 'lead'
           JOIN client_assignments a ON a.user_id = u.id AND a.client_id = ?
           WHERE u.is_active = 1 AND u.is_service = 0""",
        (client_id,),
    )
    return frozenset(r["id"] for r in rows)


def assigned_people(client_id: int) -> list:
    return get_db().execute(
        """SELECT u.id, u.full_name, GROUP_CONCAT(r.role) AS roles FROM users u
           JOIN client_assignments a ON a.user_id = u.id AND a.client_id = ?
           JOIN user_roles r ON r.user_id = u.id
           WHERE u.is_active = 1 AND u.is_service = 0
           GROUP BY u.id ORDER BY u.full_name""",
        (client_id,),
    ).fetchall()


# --- routes --------------------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE lower(email) = ? AND is_active = 1", (email,)).fetchone()
        # A service account has no password hash and can never sign in.
        if user is None or user["password_hash"] is None or not check_password_hash(
                user["password_hash"], password):
            flash("Email or password is not right.", "error")
            return render_template("login.html", email=email), 401
        session.clear()
        session["user_id"] = user["id"]
        target = request.args.get("next", "")
        # Only local paths: never redirect to another site after sign-in.
        if not target.startswith("/") or target.startswith("//"):
            target = url_for("clients.portfolio")
        return redirect(target)
    return render_template("login.html", email="")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

import math
import os
import sqlite3

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from lifecycle import ALLOWED
from roi import investment

HOURLY_RATE = 35.0

LEVERS = (
    "paid_prospecting",
    "seo_content",
    "email_traffic",
    "checkout_friction",
    "product_page",
    "trust_signals",
    "bundles",
    "cross_sell",
    "free_shipping",
)

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
    DATABASE=os.environ.get(
        "DATABASE_PATH", os.path.join(app.root_path, "marketingops.db")
    ),
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_action(action_id):
    action = get_db().execute(
        "SELECT * FROM actions WHERE id = ?", (action_id,)
    ).fetchone()
    if action is None:
        abort(404)
    return action


def parse_cost(value):
    try:
        cost = float(value or 0)
    except ValueError:
        return None
    # float() also accepts "inf" and "nan"; neither is a cost.
    if not math.isfinite(cost) or cost < 0:
        return None
    return cost


@app.route("/")
def index():
    rows = get_db().execute(
        "SELECT * FROM actions ORDER BY created_at DESC"
    ).fetchall()
    actions = [
        {
            **dict(row),
            "investment": investment(row["cost_eur"], row["cost_hours"], HOURLY_RATE),
        }
        for row in rows
    ]
    return render_template("index.html", actions=actions)


@app.route("/action/new")
def new_action():
    return render_template("new.html", levers=LEVERS, form={})


@app.route("/action", methods=["POST"])
def create_action():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    lever = request.form.get("lever", "")
    cost_eur = parse_cost(request.form.get("cost_eur"))
    cost_hours = parse_cost(request.form.get("cost_hours"))

    errors = []
    if not title:
        errors.append("Title is required.")
    elif len(title) > 200:
        errors.append("Title must be 200 characters or fewer.")
    if len(description) > 2000:
        errors.append("Description must be 2000 characters or fewer.")
    if lever not in LEVERS:
        errors.append("Choose a valid lever.")
    if cost_eur is None:
        errors.append("Cost in euros must be a number of zero or more.")
    if cost_hours is None:
        errors.append("Cost in hours must be a number of zero or more.")

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("new.html", levers=LEVERS, form=request.form), 400

    db = get_db()
    db.execute(
        "INSERT INTO actions (title, description, lever, cost_eur, cost_hours)"
        " VALUES (?, ?, ?, ?, ?)",
        (title, description or None, lever, cost_eur, cost_hours),
    )
    db.commit()
    flash("Action created.", "success")
    return redirect(url_for("index"))


@app.route("/action/<int:action_id>")
def show_action(action_id):
    action = get_action(action_id)
    next_stages = sorted(ALLOWED.get(action["status"], frozenset()))
    return render_template(
        "detail.html",
        action=action,
        investment=investment(action["cost_eur"], action["cost_hours"], HOURLY_RATE),
        hourly_rate=HOURLY_RATE,
        next_stages=next_stages,
    )


@app.route("/action/<int:action_id>/status", methods=["POST"])
def change_status(action_id):
    action = get_action(action_id)
    new_status = request.form.get("status", "")

    if new_status not in ALLOWED.get(action["status"], frozenset()):
        flash(f"Cannot move from {action['status']} to {new_status}.", "error")
        return redirect(url_for("show_action", action_id=action_id))

    db = get_db()
    db.execute(
        "UPDATE actions SET status = ? WHERE id = ?", (new_status, action_id)
    )
    db.commit()
    flash(f"Status changed to {new_status}.", "success")
    return redirect(url_for("show_action", action_id=action_id))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")

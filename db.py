"""Database connections.

One connection per request, with foreign keys switched on every time: SQLite
leaves them off by default, and on 28 October a fresh connection let a project
be deleted and left its rows orphaned.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import click
from flask import current_app, g

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "schema" / "002_v2.sql"
TEMPLATES = ROOT / "data" / "plan_templates.json"


def connect(path: str, *, must_exist: bool = True) -> sqlite3.Connection:
    """Open a connection with foreign keys on and rows addressable by name."""
    if must_exist:
        resolved = Path(path).resolve()
        try:
            conn = sqlite3.connect(f"{resolved.as_uri()}?mode=rw", uri=True)
        except sqlite3.OperationalError as error:
            raise RuntimeError(
                f"No database at {resolved}. Create it with: flask --app app init-db"
            ) from error
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def load_plan_templates(conn: sqlite3.Connection) -> int:
    """Load the 72 plans and their tags from data/plan_templates.json.

    Reference data, never edited in the app. Tags are checked against the
    metric vocabulary and the client fields' own values when loaded.
    """
    from lifecycle import METRICS

    allowed = {
        "moves": METRICS,
        "business_model": {"dtc", "b2c", "b2b", "marketplace", "subscription", "omnichannel"},
        "purchase_frequency": {"rare", "occasional", "monthly"},
    }
    data = json.loads(TEMPLATES.read_text(encoding="utf-8"))
    for p in data["plans"]:
        conn.execute(
            """INSERT INTO plan_templates (id, discipline, title, summary, benefit_type,
                   lifecycle_stage, default_window_days, default_post_period_days,
                   default_hurdle_eur, setup_hours, data_fit, featured, source_file)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (p["id"], p["discipline"], p["title"], p["summary"], p["benefit_type"],
             p["lifecycle_stage"], p["default_window_days"], p["default_post_period_days"],
             p["default_hurdle_eur"], p["setup_hours"], p["data_fit"], int(p["featured"]),
             p["source_file"]),
        )
        tags = [("moves", m) for m in p["moves"]] + [(f["kind"], f["value"]) for f in p["fits"]]
        for kind, value in tags:
            if value not in allowed[kind]:
                raise ValueError(f"plan {p['id']}: '{value}' is not a valid {kind}")
            conn.execute(
                "INSERT INTO plan_template_tags (plan_template_id, kind, value) VALUES (?, ?, ?)",
                (p["id"], kind, value),
            )
    return len(data["plans"])


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exception=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """All or nothing: commit on success, roll back on any error."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_app(app) -> None:
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Create a new, empty v2 database. Refuses to overwrite an existing file."""
        path = Path(app.config["DATABASE"])
        if path.exists():
            raise click.ClickException(
                f"{path} already exists; nothing is deleted. Move it away first."
            )
        conn = connect(str(path), must_exist=False)
        with conn:
            create_schema(conn)
            count = load_plan_templates(conn)
        conn.close()
        click.echo(f"Database ready at {path} with {count} plan templates")

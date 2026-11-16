"""Settings, read from the environment.

Nothing secret has a default that works in production: without SECRET_KEY a
random key is used for the run (sessions end when the process stops), and an
automation with no secret configured cannot call the API at all.
"""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# What each automation may do through the API (spec v2 §8). An automation can
# only write its own event types; reading /api/metrics and /api/alerts is the
# "metrics" grant, reading actions awaiting review is the "reviews" grant. Any
# signed-in automation may list the active clients (ids and names only).
AUTOMATION_SCOPES: dict[str, dict[str, frozenset[str] | bool]] = {
    "shop_intake": {"events": frozenset({"shop_data"}), "metrics": False, "reviews": False},
    "below_target_alert": {"events": frozenset({"alerts"}), "metrics": True, "reviews": False},
    "approval_routing": {"events": frozenset(), "metrics": False, "reviews": True},
    "report_draft": {"events": frozenset({"report_draft"}), "metrics": True, "reviews": False},
}

# Where each announcement goes: one Make webhook per receiving scenario.
WEBHOOK_SETTINGS = {
    "data.loaded": "MAKE_WEBHOOK_DATA_LOADED",
    "action.review_requested": "MAKE_WEBHOOK_ACTIONS",
    "action.approved": "MAKE_WEBHOOK_ACTIONS",
    "action.rejected": "MAKE_WEBHOOK_ACTIONS",
}


def make_webhooks() -> dict[str, str]:
    """Event type → Make webhook URL, for the ones configured in the environment."""
    return {event: os.environ[name] for event, name in WEBHOOK_SETTINGS.items()
            if os.environ.get(name)}


def automation_secrets() -> dict[str, str]:
    """One secret per automation, from API_SECRET_<NAME> (e.g. API_SECRET_SHOP_INTAKE)."""
    found = {}
    for name in AUTOMATION_SCOPES:
        value = os.environ.get(f"API_SECRET_{name.upper()}")
        if value:
            found[name] = value
    return found


def load(overrides: dict | None = None) -> dict:
    settings = {
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "DATABASE": os.environ.get("DATABASE_PATH", str(ROOT / "marketingops_v2.db")),
        "AUTOMATION_SECRETS": automation_secrets(),
        "MAKE_WEBHOOKS": make_webhooks(),
        "OUTBOX_SECRET": os.environ.get("OUTBOX_SECRET", ""),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
    }
    if overrides:
        settings.update(overrides)
    if not settings["SECRET_KEY"]:
        settings["SECRET_KEY"] = secrets.token_hex(32)
        settings["SECRET_KEY_IS_RANDOM"] = True
    return settings

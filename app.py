"""MarketingOps v2 — a growth consultancy tool for online stores.

Flask application factory. The rules live in lifecycle.py (workflow), roi.py
(economics) and measure.py (figures from the shop data); the routes only load
data, check access and call them.

    flask --app app init-db          # empty database with the 72 plan templates
    python scripts/generate_shop_data.py   # or: the fictional demo database
    flask --app app run
"""

import os

from flask import Flask, render_template

import auth
import config
import db
from routes import actions, admin, api, clients, components, reports, review


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    settings = config.load(overrides)
    app.config.from_mapping(settings)
    if settings.get("SECRET_KEY_IS_RANDOM"):
        app.logger.warning("SECRET_KEY is not set; using a random key for this run")

    db.init_app(app)
    auth.init_app(app)
    for module in (clients, actions, review, components, reports, admin, api):
        app.register_blueprint(module.bp)

    app.jinja_env.filters.update(eur=fmt_eur, pct=fmt_pct, num=fmt_num, label=fmt_label)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="Not found."), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", code=403,
                               message=getattr(error, "description", "Not allowed.")), 403

    return app


def fmt_eur(value, decimals: int = 0) -> str:
    if value is None:
        return "—"
    sign = "−" if value < 0 else ""
    return f"{sign}€{abs(value):,.{decimals}f}"


def fmt_pct(value, decimals: int = 1, ratio: bool = True) -> str:
    """A ratio (0.0183) or a percentage (31.2) shown as a percentage."""
    if value is None:
        return "—"
    return f"{value * 100 if ratio else value:.{decimals}f}%"


def fmt_num(value, decimals: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}"


def fmt_label(value) -> str:
    return "—" if value is None else str(value).replace("_", " ")


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")

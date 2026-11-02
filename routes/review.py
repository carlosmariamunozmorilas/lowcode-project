"""The review queue: actions waiting for the signed-in lead."""

from flask import Blueprint, g, render_template

from auth import role_required
from db import get_db

bp = Blueprint("review", __name__)


@bp.route("/review")
@role_required("lead")
def queue():
    rows = get_db().execute(
        """
        SELECT a.*, c.name AS client_name FROM actions a
        JOIN clients c ON c.id = a.client_id
        JOIN client_assignments ca ON ca.client_id = a.client_id AND ca.user_id = :me
        WHERE a.reviewer_id = :me AND a.status IN ('in_review', 'approved')
          AND a.requester_id <> :me AND COALESCE(a.owner_id, 0) <> :me
        ORDER BY a.status = 'approved', a.created_at
        """,
        {"me": g.user["id"]},
    ).fetchall()
    return render_template("review.html", actions=rows)

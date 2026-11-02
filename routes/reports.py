"""The monthly client report: an AI draft that a person reviews before it is sent.

It never goes straight from the automation to the client. Sending records
whether the reviewer corrected it; rejecting needs a reason, keeps the draft on
record, and frees the month for a new draft.
"""

import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import measure
from auth import get_client, login_required
from db import get_db, transaction

bp = Blueprint("reports", __name__)

AI_LABEL = ("AI-assisted report: drafted with AI assistance and reviewed by a person "
            "before it was sent.")


@bp.route("/clients/<int:client_id>/reports/<month>", methods=["GET", "POST"])
@login_required
def report(client_id, month):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        abort(404)
    client = get_client(client_id, write=request.method == "POST")
    conn = get_db()
    live = conn.execute(
        """SELECT * FROM client_reports WHERE client_id = ? AND month = ? AND status <> 'rejected'""",
        (client_id, month)).fetchone()

    if request.method == "POST":
        if live is None or live["status"] != "draft":
            flash("There is no draft waiting for review.", "error")
            return redirect(url_for("reports.report", client_id=client_id, month=month))
        decision = request.form.get("decision")
        if decision == "send":
            final = request.form.get("final_text", "").strip() or live["draft_text"]
            corrected = int(final != live["draft_text"].strip())
            with transaction(conn):
                conn.execute(
                    """UPDATE client_reports SET status = 'sent', final_text = ?, was_corrected = ?,
                           reviewed_by = ?, reviewed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                       WHERE id = ? AND status = 'draft'""",
                    (final, corrected, g.user["id"], live["id"]))
            flash("Report approved for sending, with the AI-assisted label.", "success")
        elif decision == "reject":
            reason = request.form.get("rejection_reason", "").strip()
            if not reason:
                flash("Rejecting a draft needs a reason.", "error")
                return redirect(url_for("reports.report", client_id=client_id, month=month))
            with transaction(conn):
                conn.execute(
                    """UPDATE client_reports SET status = 'rejected', rejection_reason = ?,
                           reviewed_by = ?, reviewed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                       WHERE id = ? AND status = 'draft'""",
                    (reason, g.user["id"], live["id"]))
            flash("Draft rejected; a new draft can be stored for this month.", "success")
        else:
            abort(400)
        return redirect(url_for("reports.report", client_id=client_id, month=month))

    history = conn.execute(
        """SELECT r.*, u.full_name AS reviewer FROM client_reports r
           LEFT JOIN users u ON u.id = r.reviewed_by
           WHERE r.client_id = ? AND r.month = ? ORDER BY r.created_at""",
        (client_id, month)).fetchall()
    return render_template("report.html", client=client, month=month, live=live,
                           history=history, label=AI_LABEL,
                           quality=measure.report_quality(conn, client_id))

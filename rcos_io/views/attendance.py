"""
Handles all of the views for the attendance system.
"""

import json
from typing import Any, Dict

from flask import (
    Blueprint,
    g,
    render_template,
    request,
    flash,
)

from rcos_io import auth
from rcos_io.services import db, attendance

bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@bp.route("/verify", methods=["POST"])
@auth.login_required
@auth.mentor_or_above_required
def verify_attendance():
    """
    Handles verifying a user ID given a meeting ID.
    """
    payload = json.loads(request.data)
    user_id = payload["user_id"]
    meeting_id = payload["meeting_id"]

    if not attendance.verify_user(user_id):
        return "Failed to verify user. Are you sure the RCS ID is spelled correct?", 400

    # get the user ID from RCS ID
    user = db.find_user_by_rcs_id(g.db_client, user_id)

    # successfully verified; submit attendence for the verified user
    db.insert_attendance(g.db_client, user["id"], meeting_id)

    return "Successfully verified!", 200


@bp.route("/attend", methods=("GET", "POST"))
@auth.login_required
@auth.rpi_required
def attend():
    """
    Handles the user's attendance view
    """

    if request.method == "GET":
        return render_template("attendance/attend.html")

    code = request.form["attendance_code"]
    user: Dict[str, Any] = g.user

    valid_code, needs_verification = attendance.validate_code(code, user["rcs_id"])

    if valid_code and not needs_verification:
        attendance_session = attendance.get_room(code)
        db.insert_attendance(g.db_client, user["id"], attendance_session["meeting_id"])

        flash("Your attendance has been recorded!", "primary")
    elif valid_code and needs_verification:
        flash(
            "You have been randomly selected to be manually verified! Please talk to"
            + " your room's Coordinator / Mentor to check in.",
            "warning",
        )
    else:
        flash("Invalid attendance code.", "danger")

    return render_template("attendance/attend.html")

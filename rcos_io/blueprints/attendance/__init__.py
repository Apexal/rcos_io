"""
Handles all of the views for the attendance system.
"""

import json
from typing import Any, Dict, List, Optional, Set, cast

from flask import (
    Blueprint,
    g,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    current_app,
)
from gql.transport.exceptions import TransportQueryError
from graphql.error import GraphQLError

from rcos_io.blueprints import auth
from rcos_io.services import database, attendance, utils

bp = Blueprint("attendance", __name__, template_folder="templates")


@bp.route("/")
@auth.mentor_or_above_required
def index():
    """Renders the attendance page for a semester or a particular meeting."""
    meeting_id: Optional[str] = request.args.get("meeting_id")

    context: Dict[str, Any] = {"meeting_id": meeting_id}
    if meeting_id:
        try:
            meeting = database.get_meeting_by_id(g.db_client, meeting_id)
            if meeting is None:
                raise utils.NotFoundError()
        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash("Yikes! Failed to fetch meeting.", "danger")
            return redirect(url_for("meetings.index"))
        except (utils.NotFoundError) as error:
            current_app.logger.exception(error)
            flash("Meeting not found.", "warning")
            return redirect(url_for("meetings.index"))

        attendances = database.get_attendances(g.db_client, meeting_id=meeting_id)

        # If we can determine who is **supposed** to attend this meeting (small group),
        # find those people and determine who did not attend
        if meeting["type"] == "small group":

            attended_user_ids: Set[str] = set()
            for user_attendance in attendances:
                attended_user_ids.add(user_attendance["user"]["id"])

            semester_id: str = meeting["semester_id"]
            small_group = database.get_mentor_small_group(
                g.db_client, semester_id, g.user["id"]
            )

            if small_group is not None:
                expected_attendee_enrollments = database.get_small_group_enrollments(
                    g.db_client, small_group["id"]
                )
                users_not_attended: List[Dict[str, Any]] = []
                for enrollment in expected_attendee_enrollments:
                    if enrollment["user"]["id"] not in attended_user_ids:
                        users_not_attended.append(enrollment["user"])
                context["small_group"] = small_group
                context["users_not_attended"] = users_not_attended

        context["meeting"] = meeting
        context["attendances"] = attendances

        return render_template("attendance/meeting.html", **context)

    return render_template("attendance/index.html", **context)


@bp.route("/verify", methods=["POST"])
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
    user = database.find_user_by_rcs_id(g.db_client, user_id)

    # successfully verified; submit attendence for the verified user
    database.insert_attendance(g.db_client, user["id"], meeting_id)

    return "Successfully verified!", 200


@bp.route("/attend", methods=("GET", "POST"))
@auth.rpi_required
def attend():
    """
    Handles the user's attendance view
    """

    if request.method == "GET":
        return render_template("attendance/attend.html")

    code = request.form["attendance_code"]
    user: Dict[str, Any] = g.user

    valid_code, needs_verification = attendance.validate_code(
        code, user["id"], user["rcs_id"]
    )

    if valid_code and not needs_verification:
        attendance_session = attendance.get_room(code)
        attendance.record_attendance(
            g.db_client, user["id"], attendance_session["meeting_id"]
        )

        flash("Your attendance has been recorded!", "primary")
    elif valid_code and needs_verification:
        flash(
            "You have been randomly selected to be manually verified! Please talk to"
            + " your room's Coordinator / Mentor to check in.",
            "warning",
        )
    else:
        flash("Invalid attendance code.", "danger")

    return redirect(url_for("attendance.attend"))

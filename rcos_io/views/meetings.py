"""
This module contains the meetings blueprint, which stores
all meeting related views and functionality.
"""
from datetime import datetime
from typing import Any, Dict, Optional, cast
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    g,
)
from graphql.error import GraphQLError
from gql.transport.exceptions import TransportQueryError

from rcos_io.services import db, attendance
from rcos_io.views.auth import (
    coordinator_or_above_required,
    login_required,
)

bp = Blueprint("meetings", __name__, url_prefix="/meetings")


@bp.route("/")
def index():
    """Renders the main meetings template."""
    return render_template("meetings/index.html")


@bp.route("/add", methods=("GET", "POST"))
@login_required
@coordinator_or_above_required
def add():
    """Renders the add meeting form and handles form submissions."""
    if request.method == "GET":

        # This list must match the meeting_types enum in the database!
        meeting_types = [
            "small group",
            "large group",
            "workshop",
            "bonus",
            "mentors",
            "coordinators",
            "other",
        ]

        return render_template("meetings/add.html", meeting_types=meeting_types)

    # HANDLE FORM SUBMISSION

    # Form new meeting dictionary for insert
    meeting_data: Dict[str, Optional[str]] = {
        "semester_id": session["semester"]["id"],
        "name": request.form["name"].strip(),
        "type": request.form["type"],
        "start_date_time": request.form["start_date_time"],
        "end_date_time": request.form["end_date_time"],
        "location": request.form["location"].strip(),
    }

    # Attempt to insert meeting into database
    try:
        new_meeting = db.insert_meeting(g.db_client, meeting_data)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Yikes! Failed to add meeting. Check logs.", "danger")
        return redirect(url_for("meetings.index"))

    # Redirect to the new meeting's detail page
    return redirect(url_for("meetings.detail", meeting_id=new_meeting["id"]))


@bp.route("/<meeting_id>")
def detail(meeting_id: str):
    """Renders the detail page for a particular meeting."""

    # Attempt to fetch meeting
    try:
        meeting = db.get_meeting_by_id(g.db_client, meeting_id)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("There was an error fetching the meeting.", "warning")
        return redirect(url_for("meetings.index"))

    # Handle meeting not found
    if meeting is None:
        flash("No meeting with that ID found!", "danger")
        return redirect(url_for("meetings.index"))

    # TODO: change this to 'is_mentor_or_above'
    can_open_attendance = session.get("is_coordinator_or_above")

    return render_template(
        "meetings/detail.html",
        meeting=meeting,
        is_authorized=can_open_attendance,
    )


@bp.route("/<meeting_id>/open")
@coordinator_or_above_required  # TODO: change to mentors or above
@login_required
def open_meeting(meeting_id: str):
    """Opens a meeting attendance room."""
    meeting = None
    small_group_id = "default"
    code = None

    try:
        meeting = db.get_meeting_by_id(g.db_client, meeting_id)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("There was an error fetching the meeting.", "warning")
        return redirect(url_for("meetings.meetings"))

    # if we're opening a small group attendance room, get the ID of the room
    if meeting["type"] == "small group":
        user: Dict[str, Any] = g.user

        try:
            small_group_id = db.get_mentor_small_group(g.db_client, user["id"])[
                "small_group_id"
            ]
        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash(
                f"There was an error fetching the small group room for user {user['id']}.",
                "warning",
            )
            return redirect(url_for("meetings.meetings"))

    # If we're in a small group room, look for <meeting_id>:<small_group_id>. If not,
    # then find <meeting_id>:default. The latter keyword determines how many unique
    # sessions can be opened. For instance, if there are 10 small group rooms, 10
    # unique sessions rooms can be opened.
    if not attendance.room_exists(meeting_id, small_group_id):
        code = attendance.register_room(meeting["location"], meeting_id, small_group_id)
    else:
        code = attendance.get_code_for_room(meeting_id, small_group_id)

    return render_template("attendance/open.html", code=code, meeting=meeting)


@bp.route("/<meeting_id>/close", methods=["POST"])
@coordinator_or_above_required
@login_required
def close(meeting_id: str):
    """Closes a room for attendance."""
    code = request.form["code"]
    attendance.close_room(code)

    return redirect(url_for("meetings.detail", meeting_id=meeting_id))


@bp.route("/api/events")
def events_api():
    """Returns a JSON array of event objects that Fullcalendar can understand."""
    start = (
        datetime.fromisoformat(cast(str, request.args.get("start")))
        if "start" in request.args
        else None
    )
    end = (
        datetime.fromisoformat(cast(str, request.args.get("end")))
        if "end" in request.args
        else None
    )

    # Fetch meetings
    meetings = db.get_meetings(
        g.db_client, only_published=True, start_at=start, end_at=end
    )

    # Convert them to objects that Fullcalendar can understand
    events = list(map(meeting_to_event, meetings))

    return events


def meeting_to_event(meeting: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a Fullcalendar event object from a meeting."""
    meeting_type = cast(str, meeting["type"]).title()
    return {
        "id": meeting["id"],
        "title": meeting["name"] or meeting_type,
        "start": meeting["start_date_time"],
        "end": meeting["end_date_time"],
        "url": f"/meetings/{meeting['id']}",
        "color": "red",  # TODO: reflect meeting type
    }

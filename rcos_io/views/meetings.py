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
from pytz import timezone

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

    return render_template(
        "meetings/detail.html",
        meeting=meeting,
    )


@bp.route("/<meeting_id>/host")
@login_required
def host(meeting_id: str):
    meeting = None

    try:
        meeting = db.get_meeting_by_id(g.db_client, meeting_id)
    except Exception as error:
        current_app.logger.exception(error)
        flash("There was an error fetching the meeting.", "warning")
        return redirect(url_for("meetings.meetings"))

    code = attendance.register_room(meeting["location"], meeting_id)

    return render_template("attendance/host.html", code=code, meeting_id=meeting_id)


@bp.route("/<meeting_id>/close", methods=["POST"])
@login_required
def close(meeting_id: str):
    code = request.args["code"]
    attendance.close_room(code)

    return url_for("meetings.detail", meeting_id=meeting_id), 200


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

from datetime import datetime
from typing import Any, Dict, Optional
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)
from pytz import timezone

from rcos_io.services.db import get_meeting_by_id, get_meetings, insert_meeting
from rcos_io.views.auth import (
    coordinator_or_above_required,
    login_required,
    rpi_required,
)

bp = Blueprint("meetings", __name__, url_prefix="/meetings")

eastern = timezone("US/Eastern")


@bp.route("/")
def meetings():
    """Renders the main meetings template which shows a calendar that fetches events from the API route."""
    return render_template("meetings/meetings.html")


@bp.route("/add", methods=("GET", "POST"))
@login_required
@coordinator_or_above_required
def add_meeting():
    """Renders the add meeting form and handles form submissions."""
    if request.method == "GET":
        meeting_types = [
            "small group",
            "large group",
            "workshop",
            "bonus",
            "mentors",
            "coordinators",
            "other",
        ]

        return render_template("meetings/add_meeting.html", meeting_types=meeting_types)
    else:

        # Add to database
        meeting_data: dict[str, Optional[str]] = {
            "semester_id": session["semester"]["id"],
            "name": request.form["name"].strip(),
            "type": request.form["type"],
            "start_date_time": request.form["start_date_time"],
            "end_date_time": request.form["end_date_time"],
            "location": request.form["location"].strip(),
        }

        try:
            new_meeting = insert_meeting(meeting_data)
        except Exception as e:
            current_app.logger.exception(e)
            flash("Yikes! Failed to add meeting. Check logs.", "danger")
            return redirect(url_for("meetings.meetings"))

        return redirect(
            url_for("meetings.meeting_detail", meeting_id=new_meeting["id"])
        )


@bp.route("/<meeting_id>")
def meeting_detail(meeting_id: str):
    try:
        meeting = get_meeting_by_id(meeting_id)
        print(meeting)
    except:
        flash("Invalid meeting ID!", "warning")
        return redirect(url_for("meetings.meetings"))

    if meeting:
        return render_template(
            "meetings/meeting_detail.html",
            meeting=meeting,
            format_date=lambda date, format: datetime.fromisoformat(date).strftime(
                format
            ),
        )
    else:
        flash("No meeting with that ID found!", "danger")
        return redirect(url_for("meetings.meetings"))


@bp.route("/api/events")
def events_api():
    """Returns a JSON array of event objects that Fullcalendar can understand."""
    # TODO: use this is filtering meetings
    # TODO: filter based on logged in status and role
    start = (
        datetime.fromisoformat(request.args.get("start"))
        if "start" in request.args
        else None
    )
    end = (
        datetime.fromisoformat(request.args.get("end"))
        if "end" in request.args
        else None
    )

    # Fetch meetings
    meetings = get_meetings()
    # Convert them to objects that Fullcalendar can understand
    events = list(map(meeting_to_event, meetings))

    return events


def meeting_to_event(meeting: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a Fullcalendar event object from a meeting."""
    return {
        "id": meeting["id"],
        "title": meeting["name"] or f"{meeting['type']} Meeting",
        "start": meeting["start_date_time"],
        "end": meeting["end_date_time"],
        "url": f"/meetings/{meeting['id']}",
        "color": "red",  # TODO: reflect meeting type
    }

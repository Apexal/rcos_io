from datetime import date, datetime, timedelta
from typing import Any, Dict
from flask import Blueprint, render_template, request, url_for
from pytz import timezone

from rcos_io.db import get_meetings

bp = Blueprint("meetings", __name__, url_prefix="/meetings")

eastern = timezone('US/Eastern')

@bp.route("/")
def meetings():
    """Renders the main meetings template which shows a calendar that fetches events from the API route."""
    return render_template("meetings/meetings.html")

@bp.route("/add", methods=("GET", "POST"))
def add_meeting():
    """Renders the add meeting form and handles form submissions."""
    if request.method == "GET":
        meeting_types = ["small_group", "large_group", "workshop", "bonus", "mentors", "coordinators", "other"]

        return render_template("meetings/add_meeting.html", meeting_types=meeting_types)
    else:
        # TODO: persist to database
        return request.form

@bp.route("/api/events")
def events_api():
    """Returns a JSON array of event objects that Fullcalendar can understand."""
    # TODO: use this is filtering meetings
    # TODO: filter based on logged in status and role
    start = datetime.fromisoformat(request.args.get("start")) if "start" in request.args else None
    end = datetime.fromisoformat(request.args.get("end")) if "end" in request.args else None

    # Fetch meetings
    meetings = get_meetings()
    # Convert them to objects that Fullcalendar can understand
    events = list(map(meeting_to_event, meetings))

    return events

def meeting_to_event(meeting: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a Fullcalendar event object from a meeting."""
    return {
        "id": meeting["id"],
        "title": meeting["name"],
        "start": meeting["start_date_time"],
        "end": meeting["end_date_time"],
        "url": f"/meetings/{meeting['id']}",
        "color": "red" # TODO: reflect meeting type
    }
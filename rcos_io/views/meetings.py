from datetime import date, datetime, timedelta
from typing import Any, Dict
from flask import Blueprint, render_template, request, url_for

bp = Blueprint("meetings", __name__)

@bp.route("/meetings")
def render_projects():
    return render_template("meetings/meetings.html")

@bp.route("/api/events")
def events():
    start = datetime.fromisoformat(request.args.get("start")) if "start" in request.args else None
    end = datetime.fromisoformat(request.args.get("end")) if "end" in request.args else None

    # TODO:
    # Fetch meetings
    # meetings = get_meetings(start=start, end=end) 
    # events = map(meeting_to_event, meetings)
    # return events

    return [{
        "title": "Small Group",
        "start": datetime.now().isoformat(),
        "end": (datetime.now() + timedelta(hours=2)).isoformat(),
        "url": "/meetings/123"
    }]

def meeting_to_event(meeting: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": meeting["id"],
        "title": meeting["name"],
        "url": url_for("meeting", meeting_id=meeting["id"]),
        "color": "red" # TODO: reflect meeting type
    }
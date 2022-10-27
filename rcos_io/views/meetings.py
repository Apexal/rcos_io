from datetime import date, datetime, timedelta
from typing import Any, Dict
from flask import Blueprint, render_template, request, url_for
from pytz import timezone

from rcos_io.db import get_meetings

bp = Blueprint("meetings", __name__)

eastern = timezone('US/Eastern')

@bp.route("/meetings")
def render_projects():
    return render_template("meetings/meetings.html")

@bp.route("/api/events")
def events():
    start = datetime.fromisoformat(request.args.get("start")) if "start" in request.args else None
    end = datetime.fromisoformat(request.args.get("end")) if "end" in request.args else None

    # TODO:
    # Fetch meetings
    meetings = get_meetings() 
    events = list(map(meeting_to_event, meetings))
    return events

def meeting_to_event(meeting: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": meeting["id"],
        "title": meeting["name"],
        "start": meeting["start_date_time"],
        "end": meeting["end_date_time"],
        "url": f"/meetings/{meeting['id']}",
        "color": "red" # TODO: reflect meeting type
    }
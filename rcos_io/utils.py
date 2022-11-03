from typing import List, Dict, Any, Optional, Tuple
from datetime import date
from flask.wrappers import Request
from flask.sessions import SessionMixin


def active_semester(semesters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Returns the semester that's either in progress or next up. Might return None if none exists.

    Expects semesters to be ordered ascending by `start_date`.
    """

    today = str(date.today())

    for semester in semesters:
        if semester["start_date"] <= today and semester["end_date"] >= today:
            return semester
        elif semester["start_date"] > today:
            return semester

    return None


def get_semester_by_id(
    semesters: List[Dict[str, Any]], semester_id: str
) -> Optional[Dict[str, Any]]:
    for semester in semesters:
        if semester["id"] == semester_id:
            return semester
    return None


def get_target_semester(
    request: Request, session: SessionMixin
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    semester_id: Optional[str] = request.args.get("semester_id") or (
        session["semester"]["id"] if "semester" in session else "all"
    )
    semester = None
    if semester_id:
        semester = get_semester_by_id(session["semesters"], semester_id)
    return semester_id, semester

"""This module contains utility functions used across the codebase."""

from typing import List, Dict, Any, Optional
from datetime import date
from flask import g
from flask.wrappers import Request
from flask.sessions import SessionMixin
from rcos_io.blueprints.database import models


class NotFoundError(Exception):
    """Custom exception for when expected data was not found."""


def get_active_semester(
    semesters: List[models.Semester], on_date: Optional[date] = date.today()
) -> Optional[models.Semester]:
    """
    Returns the semester that's either in progress or next up.

    Expects semesters to be ordered ascending by `start_date`.

    Args:
        semesters: list of semester objects
        on_date: the reference date
    Returns:
        the current or next semester OR `None` if neither exists
    """

    for semester in semesters:
        print("jere", semester)
        if semester.start_date <= on_date <= semester.end_date:
            return semester
        if semester.start_date > on_date:
            return semester

    return None


def get_semester_by_id(
    semesters: List[Dict[str, Any]], semester_id: str
) -> Optional[Dict[str, Any]]:
    """Finds a semester from a list of semester dicts by ID."""
    for semester in semesters:
        if semester["id"] == semester_id:
            return semester
    return None


def get_target_semester(request: Request, session: SessionMixin):
    """
    Determines the intended semester from the optional `semester_id` query parameter.

    Args:
        request: the current Flask request
        session: the current session object
    Returns:
        the target semester's ID or None if all semesters are desired
    Throws:
        Exception when an unknown semester id is provided
    """
    semester_id: Optional[str] = request.args.get("semester_id")

    if not semester_id and g.semester:
        semester_id = g.semester.id
    elif not semester_id or semester_id == "all":
        semester_id = None

    semester = None
    if semester_id:
        semester = get_semester_by_id(g.semesters, semester_id)

    if semester_id and not semester:
        raise NotFoundError(f"Semester {semester_id} not found")

    return semester_id, semester

# pylint: disable=W0613

"""
This module contains the meetings blueprint, which stores
all meeting related views and functionality.
"""
import functools
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, cast

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from gql.transport.exceptions import TransportQueryError
from graphql.error import GraphQLError

from rcos_io.blueprints.auth import (
    rpi_required,
    mentor_or_above_required,
)
from rcos_io.services import attendance, database, utils
from . import forms

C = TypeVar("C", bound=Callable[..., Any])

bp = Blueprint("meetings", __name__, template_folder="templates")


def for_meeting(view: C) -> C:
    """Fetches meeting from meeting_id URL parameter."""

    @functools.wraps(view)
    def wrapped_view(**kwargs: Any):
        # Attempt to fetch meeting
        try:
            meeting = database.get_meeting_by_id(g.db_client, kwargs["meeting_id"])
        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash("There was an error fetching the meeting.", "warning")
            return redirect(url_for("meetings.index"))

        # Handle meeting not found
        if meeting is None:
            flash("No meeting with that ID found!", "danger")
            return redirect(url_for("meetings.index"))

        g.meeting = meeting
        g.semester_id = meeting["semester_id"]
        g.context = {"meeting": meeting, "semester_id": g.semester_id}

        return view(**kwargs)

    return cast(C, wrapped_view)


@bp.route("/")
def index():
    """Renders the main meetings template."""
    return render_template("meetings/index.html")


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
    meetings = database.get_meetings(
        g.db_client, only_published=True, start_at=start, end_at=end
    )

    # Convert them to objects that Fullcalendar can understand
    events = list(map(meeting_to_event, meetings))

    return events


@bp.route("/add", methods=("GET", "POST"))
@mentor_or_above_required
def add():
    """Renders the add meeting form and handles form submissions."""
    form = forms.MeetingForm()
    form.type.choices = (
        [
            "small group",
            "large group",
            "workshop",
            "bonus",
            "mentors",
            "coordinators",
            "other",
        ]
        if session.get("is_coordinator_or_above")
        else ["workshop"]
    )
    if request.method == "GET":
        form.start_date_time.data = datetime.today()
        form.end_date_time.data = form.start_date_time.data + timedelta(hours=2)

    if form.validate_on_submit():
        # Mentors can only create workshops
        if form.type.data == "small_group" and not session["is_mentor_or_above"]:
            flash("Mentors can only create workshops!", "warning")
            return redirect(url_for("meetings.index"))

        # Determine the semester from the date
        semester = utils.active_semester(
            session["semesters"], form.start_date_time.data
        )
        if semester is None:
            flash("The start date is not within any known semester!", "danger")
            return redirect(url_for("meetings.add"))

        form.start_date_time.data = form.start_date_time.data.isoformat()
        form.end_date_time.data = form.end_date_time.data.isoformat()

        # Attempt to insert meeting into database
        try:
            new_meeting = database.insert_meeting(
                g.db_client, {"semester_id": semester["id"], **form.data}
            )
        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash("Yikes! Failed to add meeting. Check logs.", "danger")
            return redirect(url_for("meetings.index"))

        # Redirect to the new meeting's detail page
        return redirect(url_for("meetings.detail", meeting_id=new_meeting["id"]))

    return render_template("meetings/add.html", form=form)

    # # This list must match the meeting_types enum in the database!
    # # Mentors can only create workshops


@bp.route("/attend", methods=("GET", "POST"))
@rpi_required
def attend():
    """
    Handles the user's attendance view
    """

    if request.method == "GET":
        return render_template("meetings/attend.html")

    code = request.form["attendance_code"]
    user: Dict[str, Any] = g.user

    valid_code, needs_verification = attendance.validate_code(
        code, user["id"], user["rcs_id"]
    )

    if valid_code and not needs_verification:
        attendance_session = attendance.get_room(code)

        if attendance_session:
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

    return redirect(url_for("meetings.attend"))


@bp.route("/attendance/verify", methods=["POST"])
@mentor_or_above_required
def verify_attendance():
    """
    Handles verifying a user ID given a meeting ID.
    """
    payload: Optional[Dict[str, Any]] = request.json
    print(payload)
    if payload is None:
        return "Missing payload", 400

    user_id = payload["user_id"]
    meeting_id = payload["meeting_id"]

    if not attendance.verify_user(user_id):
        return "Failed to verify user. Are you sure the RCS ID is spelled correct?", 400

    # get the user ID from RCS ID
    user = database.find_user_by_rcs_id(g.db_client, user_id)
    print(user)
    if user is None:
        return "Can't find user with that RCS ID!", 400

    # successfully verified; submit attendence for the verified user
    database.insert_attendance(g.db_client, user["id"], meeting_id)

    return "Successfully verified!", 200


@bp.route("/<meeting_id>")
@for_meeting
def detail(meeting_id: str):
    """Renders the detail page for a particular meeting."""
    g.context["can_open_attendance"] = session.get("is_mentor_or_above")

    return render_template(
        "meetings/detail.html",
        **g.context,
    )


@bp.route("/<meeting_id>/edit")
@for_meeting
def edit(meeting_id: str):
    """Renders the edit page for a particular meeting."""
    form = forms.MeetingForm()

    # if form.validate_on_submit():

    return render_template("meetings/edit.html", **g.context, form=form)


@bp.route("/<meeting_id>/attendance")
@mentor_or_above_required
@for_meeting
def meeting_attendance(meeting_id: str):
    """Renders the attendance page for a particular meeting."""

    # For type checking since g does not have types
    context: Dict[str, Any] = g.context
    meeting: Dict[str, Any] = g.meeting
    semester_id: str = g.semester_id

    # Determine if we care about a particular small group
    small_group_id: Optional[str] = request.args.get("small_group_id")
    small_group: Optional[Dict[str, Any]] = None
    if small_group_id is None:
        small_group = database.get_mentor_small_group(
            g.db_client, semester_id, g.user["id"]
        )
    else:
        small_group = database.get_small_group(g.db_client, small_group_id)

    # If we have a small group ID, make sure it's real
    if small_group_id and not small_group:
        flash("Small group not found.", "warning")
        return redirect(url_for("meetings.meeting_attendance", meeting_id=meeting_id))

    # Get this meeting's attendances
    attendances = database.get_attendances(
        g.db_client, meeting_id=meeting_id, small_group_id=small_group_id
    )

    # If we can determine who is **supposed** to attend this meeting (small group),
    # find those people and determine who did not attend
    non_attendance_users: List[Dict[str, Any]] = []

    # If it is a typical meeting, we know who to expect there and who went versus missed
    if meeting["type"] not in ["mentors", "coordinators"]:
        attended_user_ids: Set[str] = set(
            user_attendance["user"]["id"] for user_attendance in attendances
        )

        if small_group is None:
            expected_attendee_users = database.get_users(g.db_client, semester_id)
        else:
            expected_attendee_enrollments = database.get_small_group_enrollments(
                g.db_client, small_group["id"]
            )
            expected_attendee_users = [
                enrollment["user"] for enrollment in expected_attendee_enrollments
            ]

        non_attendance_users = [
            user
            for user in expected_attendee_users
            if user["id"] not in attended_user_ids
        ]

    context["small_group"] = small_group
    context["attendances"] = attendances
    context["non_attendance_users"] = non_attendance_users

    return render_template("meetings/meeting_attendance.html", **context)


@bp.route("/<meeting_id>/attendance/open")
@mentor_or_above_required
@for_meeting
def open_attendance(meeting_id: str):
    """Opens a meeting attendance room."""
    small_group_id = "default"

    # For type checking since g does not have types
    context: Dict[str, Any] = g.context
    meeting: Dict[str, Any] = g.meeting
    semester_id: str = g.semester_id

    # If we're opening a small group attendance room, get the ID of the room
    if meeting["type"] == "small group":
        user: Dict[str, Any] = g.user

        # Find this mentor's small group
        try:
            small_group = database.get_mentor_small_group(
                g.db_client, semester_id, user["id"]
            )
            if small_group is None:
                raise utils.NotFoundError()

            small_group_id: str = small_group["id"]
        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash(
                f"There was an error fetching the small group room for user {user['id']}.",
                "warning",
            )
            return redirect(url_for("meetings.index"))
        except utils.NotFoundError as error:
            current_app.logger.exception(error)
            flash(
                "You aren't mentoring a small group, creating a generic attendance code instead.",
                "warning",
            )

    # If we're in a small group room, look for <meeting_id>:<small_group_id>. If not,
    # then find <meeting_id>:default. The latter keyword determines how many unique
    # sessions can be opened. For instance, if there are 10 small group rooms, 10
    # unique sessions rooms can be opened.
    if not attendance.room_exists(meeting_id, small_group_id):
        context["code"] = attendance.register_room(
            meeting["location"], meeting_id, small_group_id
        )
    else:
        context["code"] = attendance.get_code_for_room(meeting_id, small_group_id)

    return render_template("meetings/open.html", **context)


@bp.route("/<meeting_id>/attendance/close", methods=["POST"])
@mentor_or_above_required
@for_meeting
def close(meeting_id: str):
    """Closes a room for attendance."""
    code = request.form["code"]
    attendance.close_room(code)

    return redirect(url_for("meetings.detail", meeting_id=meeting_id))


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

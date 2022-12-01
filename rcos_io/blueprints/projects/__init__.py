"""
This module contains the projects blueprint, which stores
all project related views and functionality.
"""
from collections import defaultdict
import functools
from typing import Any, Callable, DefaultDict, Dict, List, TypeVar, cast
from flask import (
    Blueprint,
    request,
    render_template,
    g,
    redirect,
    session,
    flash,
    url_for,
    Markup,
    current_app,
)
import bleach
import markdown
from graphql.error import GraphQLError
from gql.transport.exceptions import TransportQueryError
from rcos_io.services import utils, database
from rcos_io.blueprints import auth

C = TypeVar("C", bound=Callable[..., Any])

bp = Blueprint("projects", __name__, template_folder="templates")


def for_project(view: C) -> C:
    """Fetches project from project_id URL parameter."""

    @functools.wraps(view)
    def wrapped_view(**kwargs: Any):
        # Attempt to fetch meeting
        try:
            project = database.get_project(g.db_client, kwargs["project_id"])
        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash("There was an error fetching the project.", "warning")
            return redirect(url_for("projects.index"))

        # Handle project not found or not approved
        if project is None or (
            not project["is_approved"] and not session.get("is_coordinator_or_above")
        ):
            flash("No such project with that ID exists!", "warning")
            return redirect(url_for("projects.index"))

        is_project_lead = False
        for enrollment in project["enrollments"]:
            # Determine if the logged in user is currently a project lead
            if (
                g.is_logged_in
                and session.get("semester")
                and enrollment["semester_id"] == session.get("semester")["id"]
                and enrollment["user_id"] == session.get("user")["id"]
            ):
                is_project_lead = enrollment["is_project_lead"]

        g.project = project
        g.is_project_lead = is_project_lead
        g.context = {"project": project, "is_project_lead": is_project_lead}
        return view(**kwargs)

    return cast(C, wrapped_view)


@bp.route("/")
def index():
    """
    Get all projects for a specific semester OR for all semesters.
    """

    # Search term to filter projects on
    # TODO: use it!
    search = request.args.get("search")

    # Fetch target semester ID from url or default to current active one (which might not exist)
    try:
        semester_id, semester = utils.get_target_semester(request, session)
    except utils.NotFoundError:
        flash("No such semester found!", "warning")
        return redirect(url_for("projects.index", semester_id="all"))

    is_looking_for_members = (
        True
        if semester and request.args.get("is_looking_for_members") is not None
        else None
    )

    # Values passed to template
    context: Dict[str, Any] = {
        "search": search,
        "is_looking_for_members": is_looking_for_members,
        "semester_id": semester_id,
        "semester": semester,
    }

    # Attempt to fetch APPROVED projects
    try:
        context["projects"] = database.get_projects(
            g.db_client,
            False,
            semester_id=semester_id,
            is_looking_for_members=is_looking_for_members,
        )
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Yikes! There was an error while fetching the projects.", "danger")
        return redirect(url_for("index"))

    # Only coordinators+ need to know about unapproved projects
    if session.get("is_coordinator_or_above"):
        context["unapproved_projects"] = database.get_projects(
            g.db_client, False, is_approved=False
        )

    return render_template("projects/index.html", **context)


@bp.route("/add", methods=("GET", "POST"))
@auth.rpi_required
def add():
    """
    Renders the new project form on GET request.
    Handles form submission and adding to DB on POST request.
    """
    if request.method == "GET":
        return render_template("projects/add.html")

    # Handle POST form submission and to add project

    # Extract form values
    name = request.form["name"]
    short_description = request.form["short_description"]
    description_markdown = request.form["description_markdown"]

    # Parse tags from comma-separated string and wrap in quotes to form postgres strings
    tags = list(set(f'"{s.strip().lower()}"' for s in request.form["tags"].split(",")))

    user: Dict[str, Any] = g.user
    project_data = {
        "owner_id": user["id"],
        "name": name,
        "short_description": short_description,
        "description_markdown": description_markdown,
        "tags": "{" + ",".join(tags) + "}",  # Postgres array literal {"val", "val"}
    }

    try:
        inserted_project = database.add_project(g.db_client, project_data)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Oops! There was en error while submitting the project.", "danger")
        return redirect(url_for("projects.index"))
    #
    #   TODO: send approval request to Discord
    #

    flash(
        "Woo hoo! You proposed a new project. "
        "Coordinators will review it and approve it or reach out to you. "
        "It will not be listed until it is approved.",
        "success",
    )

    return redirect(url_for("projects.detail", project_id=inserted_project["id"]))


@bp.route("/approve", methods=("GET", "POST"))
@auth.coordinator_or_above_required
def approve():
    """Renders the list of **unapproved** projects and handles verifying them."""
    if request.method == "GET":
        try:
            unapproved_projects = database.get_projects(
                g.db_client, False, is_approved=False
            )

        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash("Yikes! There was an error while fetching the projects.", "danger")
            return redirect(url_for("projects.index"))

        return render_template(
            "projects/approve.html", unapproved_projects=unapproved_projects
        )

    # HANDLE FORM SUBMISSION

    # Extract form values
    target_project_id = request.form["project_id"]
    target_project_action = request.form["action"]

    # Confirm that the desired action is valid
    if (
        not target_project_id
        or not target_project_action
        or target_project_action not in ("approve", "deny")
    ):
        flash("Invalid action.", "danger")
        return redirect(url_for("projects.approve"))

    # Apply action
    if target_project_action == "approve":
        flash(f"Approved project {target_project_id}", "success")
    else:
        # TODO: actually deny project
        flash(f"Denied user {target_project_id}", "info")

    return redirect(url_for("projects.approve"))


@bp.route("/<project_id>")
@for_project
def detail(project_id: str):
    """Renders the detail page for a specific project."""

    # Group enrollments by semesters
    enrollments_by_semester_id: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(
        lambda: []
    )

    for enrollment in g.project["enrollments"]:
        enrollments_by_semester_id[enrollment["semester_id"]].append(enrollment)

    # Sanitize the project's markdown description to remove any sketchy HTML
    # This prevents Cross-Site Scripting (XSS) attacks (hopefully...)
    compiled_md = markdown.markdown(g.project["description_markdown"])
    g.project["description_markdown"] = Markup(
        bleach.clean(
            compiled_md,
            tags=[
                "b",
                "i",
                "p",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "a",
                "code",
                "ul",
                "li",
                "ol",
                "em",
                "strong",
            ],
        )
    )

    return render_template(
        "projects/detail.html",
        **g.context,
        enrollments_by_semester_id=enrollments_by_semester_id,
    )


@bp.route("/<project_id>/addmember", methods=("POST",))
@auth.setup_required
@for_project
def add_member(project_id: str):
    """Handles upserting a new project enrollment."""

    if not g.is_project_lead:
        flash("Only current project leads can add team members!", "danger")
        return redirect(url_for("projects.detail", project_id=project_id))

    semester_id = request.form["semester_id"]
    user_identifier = request.form["user_identifier"]
    credit_count = int(request.form["credits"])

    # TODO: error handle
    user = database.get_user(g.db_client, email=user_identifier, rcs_id=user_identifier)

    if user is None:
        flash("Student not found!", "danger")
        return redirect(url_for("projects.detail", project_id=project_id))

    # TODO: error handle
    database.set_enrollment(
        g.db_client,
        {
            "semester_id": semester_id,
            "user_id": user["id"],
            "project_id": project_id,
            "credits": credit_count,
        },
    )

    flash(f"Added {user['display_name']} to the team!", "success")
    return redirect(url_for("projects.detail", project_id=project_id))

"""
This module contains the projects blueprint, which stores
all project related views and functionality.
"""
from typing import Any, Dict
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

bp = Blueprint("projects", __name__, url_prefix="/projects")


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

    # Values passed to template
    context: Dict[str, Any] = {
        "search": search,
        "semester_id": semester_id,
        "semester": semester,
    }

    # Attempt to fetch projects
    try:
        all_projects = database.get_projects(g.db_client, False, semester_id)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Yikes! There was an error while fetching the projects.", "danger")
        return redirect(url_for("index"))

    context["approved_projects"] = []
    context["unapproved_projects"] = []

    for project in all_projects:
        if project["is_approved"]:
            context["approved_projects"].append(project)
        else:
            context["unapproved_projects"].append(project)

    return render_template("projects/index.html", **context)


@bp.route("/add", methods=("GET", "POST"))
@auth.login_required
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
    name = request.form["project_name"]
    desc = request.form["project_desc"]
    stack = request.form["project_stack"]

    # separate each technology in the list string
    # into separate strings and then trim extra whitespace
    stack = list(set(s.strip().lower() for s in stack.split(",")))

    user: Dict[str, Any] = g.user
    project_data = {
        "owner_id": user["id"],
        "name": name,
        "description_markdown": desc,
        "tags": stack,
    }

    try:
        inserted_project = database.add_project(g.db_client, project_data)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Oops! There was en error while submitting the project.", "danger")
        return redirect(url_for("projects.index"))
    #
    #   TODO: send validation to Discord, validation panel in site
    #

    return redirect(url_for("projects.detail", project_id=inserted_project["id"]))


@bp.route("/approve", methods=("GET", "POST"))
@auth.login_required
@auth.coordinator_or_above_required
def approve():
    """Renders the list of **unapproved** projects and handles verifying them."""
    if request.method == "GET":
        try:
            unapproved_projects = [
                project
                for project in database.get_projects(
                    g.db_client, False, semester_id=None
                )
                if not project["is_approved"]
            ]

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
def detail(project_id: str):
    """Renders the detail page for a specific project."""

    # Fetch target semester ID from url or default to current active one (which might not exist)
    semester_id, semester = utils.get_target_semester(request, session)

    # Values passed to template
    context: Dict[str, Any] = {
        "semester_id": semester_id,
        "semester": semester,
    }

    # Attempt to fetch project
    try:
        project = database.get_project(g.db_client, project_id)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Invalid project ID!", "danger")
        return redirect(url_for("projects.index"))

    # Handle project not found
    if project is None:
        flash("No such project with that ID exists!", "warning")
        return redirect(url_for("projects.index"))

    # TODO: semester-specific project pages via ?semester_id
    # parse out any project members that are *not* in the project this semester
    project["enrollments"] = list(
        filter(
            lambda user: user["semester"]["id"] == session["semester"]["id"],
            project["enrollments"],
        )
    )

    # Sanitize the project's markdown description to remove any sketchy HTML
    # This prevents Cross-Site Scripting (XSS) attacks (hopefully...)
    compiled_md = markdown.markdown(project["description_markdown"])
    context["full_description"] = Markup(
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

    return render_template("projects/detail.html", **context)
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
from datetime import date
from typing import Any, Dict, List, Optional
import bleach
import markdown
from rcos_io import utils

import rcos_io.services.db as db
import rcos_io.views.auth as auth

bp = Blueprint("projects", __name__, url_prefix="/projects")


@bp.route("/")
def list():
    """
    Get all projects for a specific semester OR for all semesters.
    """

    # Search term to filter projects on
    # TODO: use it!
    search = request.args.get("search")

    # Fetch target semester ID from url or default to current active one (which might not exist)
    semester_id, semester = utils.get_target_semester(request, session)

    # Values passed to template
    context: Dict[str, Any] = {
        "search": search,
        "semester_id": semester_id,
        "semester": semester,
    }

    # If there is a desired semester id, attempt to fetch projects for that semester
    if semester_id and semester_id != "all":
        # Check that it is a valid semester
        if not semester:
            flash("No such semester found!", "warning")
            return redirect(url_for("projects.list", semester_id="all"))

        # Attempt to fetch projects
        try:
            all_projects = db.get_semester_projects(
                g.db_client, semester_id, False
            )
        except Exception as e:
            current_app.logger.exception(e)
            flash("Yikes! There was an error while fetching the projects.", "danger")
            return redirect(url_for("index"))
    else:
        # Attempt to fetch projects across all semesters
        try:
            all_projects = db.get_all_projects(g.db_client)
        except Exception as e:
            current_app.logger.exception(e)
            flash("Oops! There was an error while fetching the projects.", "danger")
            return redirect(url_for("index"))

    context["approved_projects"] = []
    context["unapproved_projects"] = []

    for project in all_projects:
        if project["is_approved"]:
            context["approved_projects"].append(project)
        else:
            context["unapproved_projects"].append(project)

    return render_template("projects/projects_list.html", **context)


@bp.route("/add", methods=("GET", "POST"))
@auth.login_required
@auth.rpi_required
def add():
    if request.method == "GET":
        return render_template("projects/add_project.html")
    else:
        # Extract form values
        name = request.form["project_name"]
        desc = request.form["project_desc"]
        stack = request.form["project_stack"]

        # separate each technology in the list string
        # into separate strings and then trim extra whitespace
        stack = list(set([s.strip().lower() for s in stack.split(",")]))

        user: Dict[str, Any] = g.user
        project_data = {
            "owner_id": user["id"],
            "name": name,
            "description_markdown": desc,
            "tags": stack
        }

        try:
            inserted_project = db.add_project(g.db_client, project_data)
        except Exception as e:
            current_app.logger.exception(e)
            flash("Oops! There was en error while submitting the project.", "danger")
            return redirect(url_for("projects.projects_list"))
        #
        #   TODO: send validation to Discord, validation panel in site
        #

        return redirect(
            url_for("projects.detail", project_id=inserted_project["id"])
        )


@bp.route("/approve", methods=("GET", "POST"))
@auth.login_required
@auth.coordinator_or_above_required
def approve():
    """Renders the list of **unapproved** projects and handles verifying them."""
    if request.method == "GET":
        try:
            unapproved_projects = [project for project in db.get_all_projects(g.db_client) if not project["is_approved"]]

        except Exception as e:
            current_app.logger.exception(e)
            flash("Yikes! There was an error while fetching the projects.", "danger")
            return redirect(url_for("projects.project_list"))

        return render_template("projects/approve_projects.html", unapproved_projects=unapproved_projects)
    else:
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

    # Attempt to fetch project
    try:
        project = db.get_project(g.db_client, project_id)
    except Exception as e:
        current_app.logger.exception(e)
        flash("Invalid project ID!", "danger")
        return redirect(url_for("projects.list"))

    # Handle project not found
    if project is None:
        flash("No such project with that ID exists!", "warning")
        return redirect(url_for("projects.list"))

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
    sanitized_md = Markup(
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
        "projects/project_detail.html",
        project=project,
        full_description=sanitized_md,
        semester=session["semester"],
    )

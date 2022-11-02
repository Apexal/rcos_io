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
from typing import Any, Dict, List
import bleach
import markdown

import rcos_io.services.db as db
import rcos_io.views.auth as auth

bp = Blueprint("projects", __name__, url_prefix="/projects")


def get_current_semester():
    """
    Calculate which semester we are in given today's date.
    """
    current_date = date.today()
    start_month = "01"

    if current_date.month >= 5 and current_date.month < 8:
        start_month = "05"
    elif current_date.month >= 8:
        start_month = "08"

    return "%d%s" % (current_date.year, start_month)


@bp.route("/")
def current_projects():
    """
    Get all projects for the current semester.
    """
    if "semester" in session:
        semester_projects = db.get_semester_projects(session["semester"]["id"], False)
        return render_template(
            "projects/projects.html",
            semester=session["semester"],
            projects=semester_projects,
        )
    else:
        flash("There's no active semester of RCOS right now!", "warning")
        return redirect(url_for("index"))


@bp.route("/all")
def all_projects():
    """
    Get all projects for all semesters, current semester included.
    """
    projects = db.get_all_projects()
    return render_template("projects/projects.html", projects=projects)


@bp.route("/add", methods=("GET", "POST"))
@auth.login_required
@auth.rpi_required
def add_project():
    if request.method == "POST":
        name = request.form["project_name"]
        desc = request.form["project_desc"]
        stack = request.form["project_stack"]

        # separate each technology in the list string
        # into separate strings and then trim extra whitespace
        stack = list(set([s.strip().lower() for s in stack.split(",")]))

        user: Dict[str, Any] = g.user
        inserted_project = db.add_project(user["id"], name, desc)["returning"]

        #
        #   TODO: send validation to Discord, validation panel in site
        #

        # mark the creator of the project as the project lead
        db.add_project_lead(
            inserted_project[0]["id"], user["id"], get_current_semester(), 4
        )

        if len(inserted_project) > 0:
            return redirect(
                url_for("projects.project_detail", project_id=inserted_project[0]["id"])
            )

    return render_template("projects/add_project.html")


@bp.route("/<project_id>")
def project_detail(project_id: str):
    try:
        project = db.get_project(project_id)
    except Exception as e:
        current_app.logger.exception(e)
        flash("Invalid project ID!", "danger")
        return redirect(url_for("projects.current_projects"))

    if project is None:
        flash("No such project with that ID exists!", "warning")
        return redirect(url_for("projects.current_projects"))

    # parse out any project members that are *not* in the project this semester
    project["enrollments"] = list(
        filter(
            lambda user: user["semester"]["id"] == session["semester"]["id"],
            project["enrollments"],
        )
    )

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

from uuid import uuid4
from flask import Blueprint, request, render_template, g, redirect
from datetime import date
from typing import Any, Dict, List

import rcos_io.db as db
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




def render_projects(projects: List[Any]):
    """
        Render the projects page given a list of projects.
    """
    return render_template("projects/projects.html", projects=projects)




@bp.route("/<semester>")
def semester_projects(semester: str = None):
    """
        Get all projects for a specific semester.
    """
    if semester == None:
        return render_projects([], False)

    return render_projects(db.get_semester_projects(semester, False))




@bp.route("/")
def current_projects():
    """
        Get all projects for the current semester.
    """
    return render_projects(db.get_semester_projects(get_current_semester(), False))




@bp.route("/past")
def past_projects():
    """
        Get all projects for all past semesters, current semester included.
    """
    return render_projects(db.get_all_projects())


@bp.route("/add", methods=("GET", "POST"))
@auth.login_required
def add_project():
    if request.method == "POST":
        name = request.form["project_name"]
        desc = request.form["project_desc"]
        stack = request.form["project_stack"]

        # separate each technology in the list string
        # into separate strings and then trim extra whitespace
        stack = [s.strip() for s in stack.split(",")]

        user: Dict[str, Any] = g.user
        inserted_project = db.add_project(str(uuid4()), user["id"], name, desc)[
            "returning"
        ]

        #
        #   TODO: send validation to Discord, validation panel in site
        #

        # mark the creator of the project as the project lead
        db.add_project_lead(inserted_project[0]["id"], user["id"], get_current_semester(), 4)

        if len(inserted_project) > 0:
            return redirect("/project/%s" % (inserted_project[0]["id"]))

    return render_template("projects/add_project.html")


@bp.route("/<project_id>")
def project(project_id: str):
    project = db.get_project(project_id)

    if len(project) == 1:
        project = project[0]

        # get all semesters where the project had members
    # semesters = set([ user['semester']['id'] for user in project['enrollments'] ])
    # members_by_semester = {}

    # for s in semesters:
    #     members_by_semester[s] = []

    # for user in project['enrollments']:
    #     members_by_semester.get(user['semester']['id']).append(user)

    # project['assignments'] = members_by_semester

    return render_template("projects/project.html", project=project)

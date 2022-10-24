from flask import Flask, Blueprint, request, render_template
from datetime import date
from typing import Any, Dict, List

import rcos_io.db as db
import rcos_io.auth as auth

bp = Blueprint('projects', __name__)

'''
    Calculate which semester we are in given today's date.
'''
def get_current_semester():
    current_date = date.today()
    start_month = "01"

    if current_date.month >= 5 and \
        current_date.month < 8:
        start_month = "05"
    elif current_date.month >= 8:
        start_month = "08"

    return "%d%s" % (current_date.year, start_month)

'''
    Render the projects page given a list of projects.
'''
def render_projects(projects: List[Any]):
    return render_template("projects/projects.html", projects=projects)

'''
    Get all projects for a specific semester.
'''
@bp.route("/projects/<semester>")
def semester_projects(semester: str = None):  
    if semester == None:
        return render_projects([], False)
    
    return render_projects(db.get_semester_projects(semester, False))

'''
    Get all projects for the current semester.
'''
@bp.route("/projects")
def current_projects():
    return render_projects(db.get_semester_projects(get_current_semester(), False))

'''
    Get all projects for all past semesters, current semester included.
'''
@bp.route("/projects/past")
def past_projects():
    return render_projects(db.get_all_projects())

@bp.route("/project/<project_id>")
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

@bp.route("/project/add", methods = ('GET', 'POST'))
@auth.login_required
def add_project():
    if request.method == 'POST':
        name = request.form['project_name']
        desc = request.form['project_desc']
        stack = request.form['project_stack']

        # separate each technology in the list string 
        # into separate strings and then trim extra whitespace
        stack = [s.strip() for s in stack.split(',')]

        print(name, desc, stack)

        # TODO: persist this data to the database
    
    return render_template("projects/add_project.html")
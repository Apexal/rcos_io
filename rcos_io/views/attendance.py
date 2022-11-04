from datetime import date
import functools
from typing import Any, Dict, Optional, Union
from urllib.error import HTTPError

from rcos_io.services import db, attendance, auth
from rcos_io import settings, utils

from flask import (
    current_app,
    Blueprint,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)

bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@bp.route("/host")
@auth.login_required
@auth.mentor_or_above_required
def new_attendance():
    code = attendance.register_room()

    return render_template("attendance/host.html", code=code)


@bp.route("/verify")
@auth.login_required
@auth.mentor_or_above_required
def verify_attendance():
    attendance.verify_user("...")

    return render_template("attendance/host.html")


@bp.route("/attend")
@auth.login_required
@auth.rpi_required
def attend():
    if request.method == "GET":
        return render_template("attendance/attend.html")
    else:
        code = request.form["attendance_code"]
        user: Dict[str, Any] = g.user

        valid_code, needs_verification = attendance.validate_code(code, user["id"])

        if valid_code and not needs_verification:
            flash("Your attendance has been recorded!")
            return redirect(url_for(""))
        elif valid_code and needs_verification:
            flash(
                "You have been randomly selected to be verified by a Mentor!", "warning"
            )
            return redirect(url_for(""))

        flash("Invalid attendance code.", "warning")
        return redirect(url_for(""))

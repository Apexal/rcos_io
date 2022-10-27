from flask import Blueprint, render_template

bp = Blueprint("members", __name__, url_prefix="/members")

@bp.route("/")
def members():
    return render_template("members/members.html")
from flask import Blueprint, render_template, redirect, url_for, flash

from rcos_io.db import find_user_by_id
from rcos_io.discord import generate_nickname

bp = Blueprint("members", __name__, url_prefix="/members")


@bp.route("/")
def members():
    """Renders the lists of members (users)."""

    return render_template("members/members.html")


@bp.route("/<user_id>")
def member(user_id: str):
    """Renders a specific user's profile."""
    user = find_user_by_id(user_id, True)
    

    # User might be found or not found
    if user:
        display_name = generate_nickname(user)
        return render_template("members/member.html", user=user, display_name=display_name)
    else:
        flash("No user exists with that ID!", "warning")
        return redirect(url_for("index"))

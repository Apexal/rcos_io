from typing import Any, Dict
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session

from rcos_io.services.db import find_user_by_id, get_unverified_users, update_user_by_id
from rcos_io.services import discord
from rcos_io.views.auth import coordinator_or_above_required, login_required

bp = Blueprint("members", __name__, url_prefix="/members")


@bp.route("/")
def members():
    """Renders the lists of members (users)."""

    return render_template("members/members.html")


@bp.route("/verify", methods=("GET", "POST"))
@login_required
@coordinator_or_above_required
def verify():
    """Renders the list of **unverified** members and handles verifying them."""
    if request.method == "GET":
        unverified_users = get_unverified_users()

        return render_template("members/verify.html", unverified_users=unverified_users)
    else:
        target_user_id = request.form["user_id"]
        target_user_action = request.form["action"]

        if (
            not target_user_id
            or not target_user_action
            or target_user_action not in ("verify", "delete")
        ):
            flash("Invalid action.", "danger")
            return redirect(url_for("members.verify"))

        # Apply action
        if target_user_action == "verify":
            flash(f"Verified user {target_user_id}", "success")
            update_user_by_id(target_user_id, {"is_verified": True})
        else:
            # TODO
            flash(f"Deleted user {target_user_id}", "info")

        return redirect(url_for("members.verify"))


@bp.route("/<user_id>")
def member_detail(user_id: str):
    """Renders a specific user's profile."""

    try:
        user = find_user_by_id(user_id, True)
    except:
        flash("That is not a valid user ID!", "warning")
        return redirect(url_for("index"))

    # User might be found or not found
    # Also, only show unverified users to admins so they can approve or deny them
    if user and (user["is_verified"] or session.get("is_coordinator_or_above")):
        display_name = generate_display_name(user, g.is_logged_in)

        if user["discord_user_id"]:
            discord_user = discord.get_user(user["discord_user_id"])
        else:
            discord_user = None

        return render_template(
            "members/member.html",
            user=user,
            display_name=display_name,
            discord_user=discord_user,
        )
    else:
        flash("No user exists with that ID!", "warning")
        return redirect(url_for("index"))


def generate_display_name(user: Dict[str, Any], is_logged_in: bool) -> str:
    if is_logged_in:
        if user["first_name"] and user["last_name"]:
            name = user["first_name"] + " " + user["last_name"]
        elif user["rcs_id"]:
            name = user["rcs_id"]
        else:
            name = "Unnamed User"
    else:
        if user["first_name"] and user["last_name"]:
            name = user["first_name"] + " " + user["last_name"][0]
        else:
            name = "Unnamed User"

    return name

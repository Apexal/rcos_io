from typing import Any, Dict
from flask import Blueprint, render_template, redirect, url_for, flash, g

from rcos_io.services.db import find_user_by_id
from rcos_io.services import discord

bp = Blueprint("members", __name__, url_prefix="/members")


@bp.route("/")
def members():
    """Renders the lists of members (users)."""

    return render_template("members/members.html")


@bp.route("/<user_id>")
def member(user_id: str):
    """Renders a specific user's profile."""

    try:
        user = find_user_by_id(user_id, True)
    except:
        flash("That is not a valid user ID!", "warning")
        return redirect(url_for("index"))

    # User might be found or not found
    if user and user["is_verified"]:
        display_name = generate_display_name(user, g.is_logged_in)

        if user["discord_user_id"]:
            discord_user = discord.get_user(user["discord_user_id"])
        else:
            discord_user = None

        return render_template("members/member.html", user=user, display_name=display_name, discord_user=discord_user)
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
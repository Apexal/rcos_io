from typing import Any, Dict, Optional
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    session,
    current_app,
)
from rcos_io import utils

from rcos_io.services import db, discord
from rcos_io.views.auth import coordinator_or_above_required, login_required

bp = Blueprint("members", __name__, url_prefix="/members")


@bp.route("/")
def members_list():
    """Gets all users enrolled for a specific semester OR for all semesters."""

    # Search term to filter users on
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

    # If there is a desired semester id, attempt to fetch users enrolled for that semester
    if semester_id and semester_id != "all":
        # Check that it is a valid semester
        if not semester:
            flash("No such semester found!", "warning")
            return redirect(url_for("members.members_list", semester_id="all"))

        try:
            # Grab the users who were enrolled in that semester, and the semester object
            context["users"] = db.get_semester_users(g.db_client, semester_id)
        except Exception as e:
            current_app.logger.exception(e)
            flash("Failed to fetch members...", "danger")
            return redirect(url_for("members.members_list", semester_id="all"))
    else:
        # Attempt to fetch users across all semesters
        try:
            context["users"] = db.get_all_users(g.db_client)
        except Exception as e:
            current_app.logger.exception(e)
            flash("Oops! There was an error while fetching members.", "danger")
            return redirect(url_for("index"))

    return render_template("members/members_list.html", **context)


@bp.route("/verify", methods=("GET", "POST"))
@login_required
@coordinator_or_above_required
def verify():
    """Renders the list of **unverified** members and handles verifying them."""
    if request.method == "GET":
        unverified_users = db.get_unverified_users(g.db_client)

        return render_template("members/verify.html", unverified_users=unverified_users)
    else:
        # Extract form values
        target_user_id = request.form["user_id"]
        target_user_action = request.form["action"]

        # Confirm that the desired action is valid
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
            db.update_user_by_id(g.db_client, target_user_id, {"is_verified": True})
        else:
            # TODO: actually delete user
            flash(f"Deleted user {target_user_id}", "info")

        return redirect(url_for("members.verify"))


@bp.route("/<user_id>")
def member_detail(user_id: str):
    """Renders a specific user's profile."""

    try:
        user = db.find_user_by_id(g.db_client, user_id, True)
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
            "members/member_detail.html",
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

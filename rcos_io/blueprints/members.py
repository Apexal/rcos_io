"""
This module contains the members blueprint, which stores
all user related views and functionality.
"""
from typing import Any, Dict, List, cast
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
from graphql.error import GraphQLError
from gql.transport.exceptions import TransportQueryError
from rcos_io.services import database, discord, utils
from rcos_io.blueprints.auth import coordinator_or_above_required, login_required

bp = Blueprint("members", __name__, url_prefix="/members")


@bp.route("/")
def index():
    """Gets all users enrolled for a specific semester OR for all semesters."""

    # Search term to filter users on
    # TODO: use it!
    search = request.args.get("search")

    # Fetch target semester ID from url or default to current active one (which might not exist)
    try:
        semester_id, semester = utils.get_target_semester(request, session)
    except utils.NotFoundError:
        flash("No such semester found!", "warning")
        return redirect(url_for("members.index", semester_id="all"))

    # Values passed to template
    context: Dict[str, Any] = {
        "search": search,
        "semester_id": semester_id,
        "semester": semester,
    }

    try:
        all_users = database.get_users(g.db_client, semester_id)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Yikes! Failed to fetch users.", "danger")
        return redirect(url_for("members.index", semester_id="all"))

    context["verified_users"] = cast(List[Dict[str, Any]], [])
    context["unverified_users"] = cast(List[Dict[str, Any]], [])

    for user in all_users:
        if user["is_verified"]:
            context["verified_users"].append(user)
        else:
            context["unverified_users"].append(user)

    return render_template("members/index.html", **context)


@bp.route("/verify", methods=("GET", "POST"))
@login_required
@coordinator_or_above_required
def verify():
    """Renders the list of **unverified** members and handles verifying them."""
    if request.method == "GET":
        try:
            unverified_users: List[Dict[str, Any]] = list(
                filter(
                    lambda user: not user["is_verified"],
                    database.get_users(g.db_client, None),
                )
            )
        except (GraphQLError, TransportQueryError) as error:
            current_app.logger.exception(error)
            flash(
                "Yikes! There was an error while fetching unverified users.", "danger"
            )
            return redirect(url_for("members.index"))

        return render_template("members/verify.html", unverified_users=unverified_users)

    # HANDLE FORM SUBMISSION
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
        database.update_user_by_id(g.db_client, target_user_id, {"is_verified": True})
    else:
        # TODO: actually delete user
        flash(f"Deleted user {target_user_id}", "info")

    return redirect(url_for("members.verify"))


@bp.route("/<user_id>")
def detail(user_id: str):
    """Renders a specific user's profile."""

    try:
        user = database.find_user_by_id(g.db_client, user_id, True)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("That is not a valid user ID!", "warning")
        return redirect(url_for("index"))

    # User might be found or not found
    # Also, only show unverified users to admins so they can approve or deny them
    if user and (user["is_verified"] or session.get("is_coordinator_or_above")):
        if user["discord_user_id"]:
            discord_user = discord.get_user(user["discord_user_id"])
        else:
            discord_user = None

        return render_template(
            "members/detail.html",
            user=user,
            discord_user=discord_user,
        )

    # Handle user not found/not verified
    flash("No user exists with that ID!", "warning")
    return redirect(url_for("index"))

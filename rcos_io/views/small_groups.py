"""
This module contains the small groups blueprint, which stores
all small group related views and functionality.
"""
from typing import Any, Dict
from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    g,
)
from graphql.error import GraphQLError
from gql.transport.exceptions import TransportQueryError
from rcos_io import utils
from rcos_io.services import db

bp = Blueprint("small_groups", __name__, url_prefix="/small_groups")


@bp.route("/")
def index():
    """
    Get all small groups for a specific semester OR for all semesters.
    """

    # Search term to filter small groups on
    # TODO: use it!
    search = request.args.get("search")

    # Fetch target semester ID from url or default to current active one (which might not exist)
    try:
        semester_id, semester = utils.get_target_semester(request, session)
    except utils.NotFoundError:
        flash("No such semester found!", "warning")
        return redirect(url_for("small_groups.index"))

    # We only care about per-semester data
    if semester is None:
        flash("No such semester exists.", "info")
        return redirect(url_for("index"))

    # Values passed to template
    context: Dict[str, Any] = {
        "search": search,
        "semester_id": semester_id,
        "semester": semester,
    }

    # Attempt to fetch small groups
    try:
        context["small_groups"] = db.get_small_groups(g.db_client, semester_id)
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Yikes! There was an error while fetching the small groups.", "danger")
        return redirect(url_for("index"))


    return context

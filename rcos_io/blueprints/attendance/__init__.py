"""
Handles all of the views for the attendance system.
"""

import json
from typing import Any, Dict, List, Optional, Set, cast

from flask import (
    Blueprint,
    g,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    current_app,
)
from gql.transport.exceptions import TransportQueryError
from graphql.error import GraphQLError

from rcos_io.blueprints import auth
from rcos_io.services import database, attendance, utils

bp = Blueprint("attendance", __name__, template_folder="templates")


@bp.route("/verify", methods=["POST"])
@auth.mentor_or_above_required
def verify_attendance():
    """
    Handles verifying a user ID given a meeting ID.
    """
    payload = json.loads(request.data)
    user_id = payload["user_id"]
    meeting_id = payload["meeting_id"]

    if not attendance.verify_user(user_id):
        return "Failed to verify user. Are you sure the RCS ID is spelled correct?", 400

    # get the user ID from RCS ID
    user = database.find_user_by_rcs_id(g.db_client, user_id)

    # successfully verified; submit attendence for the verified user
    database.insert_attendance(g.db_client, user["id"], meeting_id)

    return "Successfully verified!", 200

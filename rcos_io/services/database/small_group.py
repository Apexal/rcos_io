"""Database calls for small group-related actions."""

from typing import Any, Dict, cast
from gql import Client, gql


def get_mentor_small_group(client: Client, semester_id: str, user_id: str):
    """Get the small group that a user is mentoring for."""
    query = gql(
        """
        query GetMentorRoom($semester_id: String!, $user_id: uuid!) {
            small_group_mentors(where: {
                semester_id: {_eq: $semester_id},
                user_id: {_eq: $user_id }
            }) {
  	            small_group_id
            }
        }
        """
    )

    result = client.execute(
        query,
        variable_values={"semester_id": semester_id, "user_id": user_id},
    )

    if len(result["small_group_mentors"]) == 0:
        return None

    return cast(Dict[str, Any], result["small_group_mentors"][0])

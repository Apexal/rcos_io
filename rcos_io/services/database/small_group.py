"""Database calls for small group-related actions."""

from typing import Any, Dict, List, Optional, cast
from gql import Client, gql


def get_small_group(client: Client, small_group_id: str):
    """Fetches a particular small group by its id."""
    query = gql(
        """
        query small_group($small_group_id: uuid!) {
            small_groups_by_pk(id: $small_group_id) {
                id
                name
                location
                semester_id
            }
        }
        """
    )
    result = client.execute(query, variable_values={"small_group_id": small_group_id})
    return cast(Optional[Dict[str, Any]], result["small_groups_by_pk"])


def get_mentor_small_group(client: Client, semester_id: str, user_id: str):
    """Get the small group that a user is mentoring for."""
    query = gql(
        """
        query GetMentorRoom($semester_id: String!, $user_id: uuid!) {
            small_group_mentors(where: {
                small_group: {semester_id: {_eq: $semester_id}},
                user_id: {_eq: $user_id }
            }) {
  	            small_group_id
                small_group {
                    id
                    name
                    location
                }
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

    return cast(Dict[str, Any], result["small_group_mentors"][0]["small_group"])


def get_small_group_enrollments(client: Client, small_group_id: str):
    """Fetches the users enrolled in a specific small group."""
    query = gql(
        """
        query small_group_users($small_group_id: uuid!) {
            small_groups_by_pk(id: $small_group_id) {
                small_group_projects {
                    project {
                        enrollments {
                            user {
                                id
                                display_name
                            }
                        }
                    }
                }
            }
        }
    """
    )

    result = client.execute(query, variable_values={"small_group_id": small_group_id})
    # Flatten the result into a list of enrollments
    enrollments: List[Dict[str, Any]] = []

    if result["small_groups_by_pk"] is None:
        return cast(List[Dict[str, Any]], [])

    for small_group_project in result["small_groups_by_pk"]["small_group_projects"]:
        project = small_group_project["project"]
        enrollments += project["enrollments"]

    return enrollments

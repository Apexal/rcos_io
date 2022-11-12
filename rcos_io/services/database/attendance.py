"""Database calls for working with attendance."""

from typing import Any, Dict, List, Optional, cast
from gql import Client, gql


def insert_attendance(client: Client, user_id: str, meeting_id: str):
    """
    Insert an attendance for a meeting.
    """
    query = gql(
        """
        mutation InsertAttendance($meeting_id: uuid!, $user_id: uuid!) {
            insert_meeting_attendances_one(
                object: {meeting_id: $meeting_id, user_id: $user_id},
                on_conflict: {
                    constraint: meeting_attendances_pkey,
                    update_columns: []
                }
            ) {
                meeting_id
                user_id
            }
        }
    """
    )

    result = client.execute(
        query,
        variable_values={"user_id": user_id, "meeting_id": meeting_id},
    )

    return result["insert_meeting_attendances_one"]


def get_attendances(
    client: Client, meeting_id: Optional[str] = None, user_id: Optional[str] = None
):
    """Fetches attendances for a particular meeting AND/OR a particular user."""
    where_clause = {}

    if meeting_id:
        where_clause["meeting_id"] = {"_eq": meeting_id}

    if user_id:
        where_clause["user_id"] = {"_eq": user_id}

    query = gql(
        """
        query get_attendances($where_clause: meeting_attendances_bool_exp!) {
            meeting_attendances(where: $where_clause) {
                user {
                    id
                    display_name
                }
                is_manually_added
                created_at
            }
        }
        """
    )
    result = client.execute(query, variable_values={"where_clause": where_clause})
    return cast(List[Dict[str, Any]], result["meeting_attendances"])

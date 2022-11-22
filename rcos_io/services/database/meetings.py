"""
This module contains database CRUD operations for meetings.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from gql import Client, gql


def get_meetings(
    client: Client,
    only_published: bool,
    start_at: Optional[datetime],
    end_at: Optional[datetime],
) -> List[Dict[str, Any]]:
    """
    Fetches all meetings.
    Returns meeting name, type, start and end timestamps.
    """

    where_clause: Dict[str, Any] = {}
    if only_published:
        where_clause["is_published"] = {"_eq": "true"}

    if start_at and end_at:
        where_clause["_and"] = [
            {"start_date_time": {"_gte": start_at.isoformat()}},
            {"start_date_time": {"_lte": end_at.isoformat()}},
        ]

    query = gql(
        """
        query meetings($where_clause: meetings_bool_exp!) {
            meetings(where: $where_clause) {
                id
                name
                type
                start_date_time
                end_date_time
                meeting_attendances_aggregate {
                    aggregate {
                        count
                    }
                }
            }
        }
        """
    )
    result = client.execute(query, variable_values={"where_clause": where_clause})
    return result["meetings"]


def get_meeting(client: Client, meeting_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a particular meeting by it's ID."""
    query = gql(
        """
        query find_meeting_by_id($meeting_id: uuid!) {
            meeting: meetings_by_pk(id:$meeting_id) {
                id
                semester {
                    id
                    name
                }
                semester_id
                name
                type
                start_date_time
                end_date_time
                location
                created_at
                host {
                    id
                    display_name
                }
                meeting_attendances_aggregate {
                    aggregate {
                        count
                    }
                }
            }
        }
        """
    )
    meeting = client.execute(query, variable_values={"meeting_id": meeting_id})[
        "meeting"
    ]
    return meeting


def insert_meeting(client: Client, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a new meeting into the DB."""
    query = gql(
        """
        mutation add_meeting($meeting_data: meetings_insert_input!) {
            insert_meetings_one(object: $meeting_data) {
                id
            }
        }
        """
    )
    new_meeting = client.execute(query, variable_values={"meeting_data": meeting_data})[
        "insert_meetings_one"
    ]
    return new_meeting


def update_meeting(client: Client, meeting_id: str, meeting_data: Dict[str, Any]):
    """Updates a particular meeting."""
    query = gql(
        """
    """
    )
    result = client.execute(query)

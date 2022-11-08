"""Database calls for working with attendance."""

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

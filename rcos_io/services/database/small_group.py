"""Database calls for small group-related actions."""

from gql import Client, gql


def get_mentor_small_group(client: Client, user_id: str):
    """Get the small group that a user is mentoring for."""
    query = gql(
        """
        query GetMentorRoom($user_id: uuid!) {
            small_group_mentors(where: {user_id: {_eq: $user_id }}) {
  	            small_group_id
            }
        }
        """
    )

    result = client.execute(
        query,
        variable_values={"user_id": user_id},
    )

    return result["small_group_mentors"][0]

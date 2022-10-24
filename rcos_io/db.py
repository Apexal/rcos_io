import os
from typing import Any, Dict
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

GQL_API_URL = os.environ.get("GQL_API_URL")
HASURA_ADMIN_SECRET = os.environ.get("HASURA_ADMIN_SECRET")

transport = RequestsHTTPTransport(
    url=GQL_API_URL,
    verify=True,
    retries=3,
    headers={"x-hasura-admin-secret": HASURA_ADMIN_SECRET},
)

client = Client(transport=transport, fetch_schema_from_transport=True)

BASIC_USER_DATA_FRAGMENT_INLINE = """
fragment basicUser on users {
  id
  first_name
  last_name
  preferred_name
  role
  email
  rcs_id
  discord_user_id
  github_username
}
"""


def find_or_create_user_by_email(email: str, role: str) -> Dict[str, Any]:
    """
    Given an email and a role (to be used only when creating new user) try to find the user
    and create them if they don't exist yet.
    """
    user = find_user_by_email(email)
    if user is not None:
        return user
    else:
        return create_user_with_email(email, role)


def find_user_by_email(email: str) -> Dict[str, Any] | None:
    """Given an email, find the user with that email. Returns `None` if not found. Returns basic user data if found."""
    # First attempt to find user via email
    query = gql(
        BASIC_USER_DATA_FRAGMENT_INLINE
        + """
        query find_user($email: String!) {
            users(limit: 1, where: { email: {_eq: $email}}) {
                ...basicUser
            }
        }
    """
    )

    users = client.execute(query, variable_values={"email": email})["users"]

    if len(users) == 0:
        return None

    return users[0]


def create_user_with_email(email: str, role: str) -> Dict[str, Any]:
    """Create a new user with the given email and role. Returns basic user data."""
    query = gql(
        BASIC_USER_DATA_FRAGMENT_INLINE
        + """
    mutation insert_user($user: users_insert_input!) {
      insert_users(objects: [$user], on_conflict: {
        constraint: users_email_key,
        update_columns: []
      }) {
        returning {
          ...basicUser
        }
      }
    }
  """
    )

    user = client.execute(
        query, variable_values={"user": {"email": email, "role": role}}
    )["insert_users"]["returning"][0]

    return user

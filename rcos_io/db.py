from typing import Any, Dict, List
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from rcos_io.settings import GQL_API_URL, HASURA_ADMIN_SECRET

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


def update_user_by_id(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a user with the given ID and the given updates. Returns basic user data."""
    query = gql(
        BASIC_USER_DATA_FRAGMENT_INLINE
        + """
    mutation update_user($user_id: uuid!, $updates: users_set_input!) {
      update_users(_set: $updates, where: { id :{_eq: $user_id}}) {
        returning {
          ...basicUser
        }
      }
    }
    """
    )

    user = client.execute(
        query, variable_values={"user_id": user_id, "updates": updates}
    )["update_users"]["returning"][0]
    return user


def get_project(project_id: str) -> Dict[str, Any] | None:
    query = gql(
        """
        query GetProject($pid: uuid!) {
            projects(limit: 1, where: {id: {_eq: $pid} }) {
                name
                tags
                github_repos
                id
                description_markdown
                enrollments {
                    user {
                        rcs_id
                        first_name
                        last_name
                    }
                    semester {
                        id
                    }
                }
            }
        }
        """
    )

    result = client.execute(query, variable_values={"pid": project_id})
    return result["projects"]


def get_all_projects() -> List[Dict[str, Any]]:
    query = gql(
        """
        query {
            projects(order_by: {name: asc}) {
                id
                name
                github_repos
            }
        }
        """
    )

    result = client.execute(query, variable_values={})
    return result["projects"]


def get_semester_projects(
    semester: str, with_enrollments: bool
) -> List[Dict[str, Any]]:
    query = gql(
        """
        query SemesterProjects($semesterId: String!, $withEnrollments: Boolean!) {
          projects(order_by: {name: asc}, where: {enrollments: {_or: [{semester_id: {_eq: $semesterId}}]}}) {
              id
              name
              enrollments @include(if: $withEnrollments) {
                user {
                    id
                    first_name
                    last_name
                    graduation_int
                }
                is_project_lead
                credits
              }
          }
        }
    """
    )

    result = client.execute(
        query,
        variable_values={
            "semesterId": semester,
            "withEnrollments": with_enrollments,
        },
    )

    return result["projects"]


def add_project(id: str, owner_id: str, name: str, desc: str):
    query = gql(
        """
        mutation AddProject($id: uuid!, $owner_id: uuid!, $name: String!, $desc: String!) {
            insert_projects(objects: [
                { id: $id, owner_id: $owner_id, name: $name, description_markdown: $desc }
            ]) {
                returning {
                    id
                }
            }
        }
    """
    )

    result = client.execute(
        query,
        variable_values={"id": id, "owner_id": owner_id, "name": name, "desc": desc},
    )

    return result["insert_projects"]

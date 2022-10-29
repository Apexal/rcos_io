from datetime import datetime
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
  graduation_year
  preferred_name
  role
  email
  secondary_email
  is_secondary_email_verified
  rcs_id
  discord_user_id
  github_username
}
"""

"""
                         id -> required -> uuid
                 first_name -> optional
                  last_name -> optional
            graduation_year -> optional 
             preferred_name -> optional
                       role -> required -> rpi/external
                      email -> required
            secondary_email -> optional
is_secondary_email_verified -> default: false
                     rcs_id -> optional
            discord_user_id -> optional
            github_username -> optional
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
            users(limit: 1, where: {_or: [{email: {_eq: $email}}, {_and: [{is_secondary_email_verified: {_eq:true}, secondary_email: {_eq: $email}}]}]}) {
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
    user_values = {"email": email, "role": role}

    # Extract RCS ID from RPI email
    if role == "rpi":
        rcs_id = email.removesuffix("@rpi.edu")
        user_values["rcs_id"] = rcs_id

    user = client.execute(query, variable_values={"user": user_values})["insert_users"][
        "returning"
    ][0]

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
    """
    Fetches the project with the given ID.
    Returns project name, participants, description, tags and relevant repos.
    """
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
                    is_project_lead
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
    """
    Fetches all projects.
    Returns project name, and relevant repos.
    """
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
    """
    Fetches all projects in the current semester.
    Returns project name.
    """
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
                    graduation_year
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
    """
    Creates new project with name=name and description=desc where owner is user that has id=owner_id
    """
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


def get_meetings() -> List[Dict[str, Any]]:
    """
    Fetches all meetings.
    Returns meeting name, type, start and end timestamps.
    """
    query = gql(
        """
        query meetings {
            meetings {
                id
                name
                type
                start_date_time
                end_date_time
            }
        }
        """
    )
    result = client.execute(query)
    return result["meetings"]


def add_project_lead(project_id: str, user_id: str, semester_id: str, credits: int):
    """
    Adds user with id=user_id as project lead of project with id=project_id.
    Also adds corresponding enrollment to current semester.
    """
    query = gql(
        """
        mutation AddProjectLead($project_id: uuid!, $user_id: uuid!, $semester_id: String!, $credits: Int!) {
            insert_enrollments_one(
                object: {
                    is_project_lead: true,
                    user_id: $user_id,
                    project_id: $project_id,
                    semester_id: $semester_id,
                    credits: $credits
                },  
                on_conflict: {
                    constraint: enrollments_pkey,
                    update_columns: [ project_id, is_project_lead ]
                }
            ) {
                project_id
            }
        }
    """
    )

    result = client.execute(
        query,
        variable_values={
            "project_id": project_id,
            "user_id": user_id,
            "semester_id": semester_id,
            "credits": credits,
        },
    )

    return result["insert_enrollments_one"]

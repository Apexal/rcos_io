from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union
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
  is_verified
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


def find_or_create_user_by_email(email: str, role: str) -> Tuple[Dict[str, Any], bool]:
    """
    Given an email and a role (to be used only when creating new user) tries to find the user
    and create them if they don't exist yet.

    Returns (user, is_new)
    """
    user = find_user_by_email(email)
    if user is not None:
        return user, False
    else:
        return create_user_with_email(email, role), True


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Given an email, finds the user with that email. Returns `None` if not found. Returns basic user data if found."""
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
    """Creates a new user with the given email and role. Returns basic user data."""
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
    user_values = {"email": email, "role": role, "is_verified": role == "rpi"}

    # Extract RCS ID from RPI email
    if role == "rpi":
        rcs_id = email.removesuffix("@rpi.edu")
        user_values["rcs_id"] = rcs_id

    user = client.execute(query, variable_values={"user": user_values})["insert_users"][
        "returning"
    ][0]

    return user


def find_user_by_id(
    user_id: str, include_enrollments: bool = False
) -> Optional[Dict[str, Any]]:
    """Fetches a user with the given user_id UUID. Optionally includes their enrollments."""
    query = gql(
        """
        query find_user_by_id($user_id: uuid!, $include_enrollments: Boolean!) {
            user: users_by_pk(id: $user_id) {
                id
                email
                first_name
                last_name
                is_verified
                graduation_year
                rcs_id
                role
                discord_user_id
                github_username
                enrollments @include(if: $include_enrollments) {
                    credits
                    project {
                        id
                        name
                    }
                    semester {
                        id
                        name
                    }
                    is_project_lead
                    is_coordinator
                    is_faculty_advisor
                }
            }
        }
        """
    )
    user = client.execute(
        query,
        variable_values={
            "user_id": user_id,
            "include_enrollments": include_enrollments,
        },
    )["user"]
    return user


def update_user_by_id(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates a user with the given ID and the given updates. Returns basic user data."""
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


def get_unverified_users() -> List[Dict[str, Any]]:
    query = gql(
        """
        {
            users(where: { is_verified: {_eq: false}}) {
                id
                email
                first_name
                last_name
                created_at
            }
        }
        """
    )
    users = client.execute(query)["users"]
    return users


def get_semester_users(semester_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    query = gql(
        """
        query semester_users($semester_id: String!) {
            users(order_by: [{ full_name:asc_nulls_last}, {email: asc_nulls_last}], where: {is_verified: {_eq: true}, enrollments: {semester_id: {_eq: $semester_id}}}) {
                id
                full_name
                role
                email
                created_at
                rcs_id
                graduation_year
                github_username
                enrollments_aggregate {
                    aggregate {
                        count
                    }
                }
            }
            semester: semesters_by_pk(id: $semester_id) {
                id
                name
            }
        }
        """
    )
    result = client.execute(query, variable_values={"semester_id": semester_id})
    return result["users"], result["semester"]


def get_current_or_next_semester(search_date: date) -> Optional[Dict[str, Any]]:
    query = gql(
        """
        query current_or_next_semester($date: date!) {
            semesters(limit: 1, order_by: {start_date: asc_nulls_last}, where: {_or: [{_and: [{start_date: {_lte: $date}}, {end_date: {_gte: $date}}]}, {start_date: {_gt: $date}}]}) {
                id
                name
                type
                start_date
                end_date
            }
        }
        """
    )

    result = client.execute(
        query, variable_values={"date": search_date.strftime("%Y-%m-%d")}
    )["semesters"]
    if len(result) == 0:
        return None
    else:
        return result[0]


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the project with the given ID.
    Returns project name, participants, description, tags and relevant repos.
    """
    query = gql(
        """
        query GetProject($pid: uuid!) {
            project: projects_by_pk(id: $pid) {
                name
                tags
                github_repos
                id
                short_description
                description_markdown
                enrollments {
                    user_id
                    is_project_lead
                    user {
                        id
                        rcs_id
                        full_name
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
    return result["project"]


def get_enrollment(user_id: str, semester_id: str) -> Optional[Dict[str, Any]]:
    query = gql(
        """
        query get_enrollment($user_id: uuid!, $semester_id: String!) {
            enrollments(limit: 1, where: { user_id: { _eq: $user_id }, semester_id: { _eq: $semester_id } }) {
                is_project_lead
                is_coordinator
                is_faculty_advisor
            }
        }
        """
    )

    enrollments = client.execute(
        query, variable_values={"user_id": user_id, "semester_id": semester_id}
    )["enrollments"]
    if len(enrollments) == 0:
        return None
    else:
        return enrollments[0]


def get_all_projects() -> List[Dict[str, Any]]:
    """
    Fetches all projects.
    Returns project name, and relevant repos.
    """
    query = gql(
        """
        {
            projects(order_by: {name: asc}) {
                id
                name
                tags
                github_repos
                short_description
                created_at
            }
        }
        """
    )

    result = client.execute(query, variable_values={})
    return result["projects"]


def get_semester_projects(
    semester_id: str, with_enrollments: bool
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
            tags
            github_repos
            short_description
            created_at
            project_leads: enrollments(limit: 1, where: {is_project_lead: {_eq:true}}) @include(if: $withEnrollments) {
                user_id
                user {
                    full_name
                }
            }
            enrollments_aggregate(where: {semester_id: {_eq:$semesterId}}) {
                aggregate {
                    count
                }
            }
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
            "semesterId": semester_id,
            "withEnrollments": with_enrollments,
        },
    )

    return result["projects"]


def add_project(owner_id: str, name: str, desc: str):
    """
    Creates new project with name=name and description=desc where owner is user that has id=owner_id
    """
    query = gql(
        """
        mutation AddProject($owner_id: uuid!, $name: String!, $desc: String!) {
            insert_projects(objects: [
                { owner_id: $owner_id, name: $name, description_markdown: $desc }
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
        variable_values={"owner_id": owner_id, "name": name, "desc": desc},
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


def get_meeting_by_id(meeting_id: str) -> Optional[Dict[str, Any]]:
    query = gql(
        """
        query find_meeting_by_id($meeting_id: uuid!) {
            meeting: meetings_by_pk(id:$meeting_id) {
                id
                name
                type
                start_date_time
                end_date_time
                location
                is_remote
                created_at
                host: user {
                    id
                    full_name
                }
            }
        }
        """
    )
    meeting = client.execute(query, variable_values={"meeting_id": meeting_id})[
        "meeting"
    ]
    return meeting


def insert_meeting(meeting_data: Dict[str, Any]) -> Dict[str, Any]:
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

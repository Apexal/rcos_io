"""
This module contains all database-related functionality.

Instead of manually connecting to a relational database
and writing long SQL queries, we use Hasura to get a
nice, automatic GraphQL API for our relational database.
This means we can just write GQL queries asking for exactly
the data we want without every writing code to explain how
to actually fetch that data from the database!

We use a simple Python package called `gql` to help us
make authenticated requests to our Hasura API. We make
a new connection to Hasura for every request that comes
to the Flask webserver instead of sharing a connection
across threads because that crashes.

Learn how to write Hasura GQL queries (fetch data):
https://hasura.io/docs/latest/queries/postgres/index/

Learn how to write Hasura GQL mutations (update data):
https://hasura.io/docs/latest/mutations/postgres/index/
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from flask import g, Blueprint
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from rcos_io.services import settings

bp = Blueprint("db", __name__)


def client_factory():
    """
    Creates a new GQL client pointing to the Hasura API.

    Instead of using one client across the app, one client should be made per request
    to avoid threading errors.

    Returns:
        new GQL client
    """
    transport = RequestsHTTPTransport(
        url=settings.GQL_API_URL,
        verify=True,
        retries=3,
        headers={"x-hasura-admin-secret": settings.HASURA_ADMIN_SECRET},
    )
    return Client(transport=transport, fetch_schema_from_transport=False)


@bp.before_app_request
def attach_db_client():
    """Creates a new GQL client and attach it to the every reqest as `g.db_client`."""
    g.db_client = client_factory()


BASIC_USER_DATA_FRAGMENT_INLINE = """
fragment basicUser on users {
  id
  is_verified
  first_name
  last_name
  display_name
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


def find_or_create_user_by_email(
    client: Client, email: str, role: str
) -> Tuple[Dict[str, Any], bool]:
    """
    Given an email and a role (to be used only when creating new user) tries to find the user
    and create them if they don't exist yet.

    Returns:
        found or created user
        whether the user was newly created or not
    """
    user = find_user_by_email(client, email)

    # Create if not found
    if user is None:
        return create_user_with_email(client, email, role), True

    # Return if found
    return user, False


def find_user_by_email(client: Client, email: str) -> Optional[Dict[str, Any]]:
    """
    Given an email, finds the user with that email.

    Args:
        client: GQL client
        email: the email to search on
    Returns:
        found/created user or `None`
    """
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


def create_user_with_email(client: Client, email: str, role: str) -> Dict[str, Any]:
    """
    Creates a new user with the given email and role.

    Marks user as verified and extracts RCS ID if email ends in @rpi.edu.

    Args:
        client: GQL client
        email: email to create user with
        role: role to create user with (e.g. "rpi", "external")
    Returns:
        newly created user
    """
    query = gql(
        BASIC_USER_DATA_FRAGMENT_INLINE
        + """
        mutation insert_user($user: users_insert_input!) {
            insert_users_one(object: $user, on_conflict: {
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
        rcs_id = email.replace("@rpi.edu", "")
        user_values["rcs_id"] = rcs_id

    user = client.execute(query, variable_values={"user": user_values})[
        "insert_users_one"
    ]

    return user


def find_user_by_id(
    client: Client, user_id: str, include_enrollments: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Fetches a user with the given user_id UUID. Optionally includes their enrollments.

    Args:
        client: GQL client
        user_id: the UUID of the user to fetch
        include_enrollments: whether to also fetch the user's semester enrollments
    Returns:
        found user data or `None`
    """
    query = gql(
        """
        query find_user_by_id($user_id: uuid!, $include_enrollments: Boolean!) {
            user: users_by_pk(id: $user_id) {
                id
                email
                first_name
                last_name
                display_name
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


def find_user_by_rcs_id(
    client: Client, rcs_id: str, include_enrollments: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Fetches a user with the given user_id UUID. Optionally includes their enrollments.

    Args:
        client: GQL client
        user_id: the UUID of the user to fetch
        include_enrollments: whether to also fetch the user's semester enrollments
    Returns:
        found user data or `None`
    """
    query = gql(
        """
        query find_user_by_id($rcs_id: String!, $include_enrollments: Boolean!) {
           users(where: {rcs_id: {_eq: $rcs_id }}) {
                id
                email
                first_name
                last_name
                display_name
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
            "rcs_id": rcs_id,
            "include_enrollments": include_enrollments,
        },
    )["users"]

    return user[0]


def update_user_by_id(
    client: Client, user_id: str, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Updates a user with the given ID and the given updates.

    Args:
        client: GQL client
        user_id: UUID of user to update
        updates: dict containing fields and new values to update
    Returns:
        updated user data
    """
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


def get_users(client: Client, semester_id: Optional[str]) -> List[Dict[str, Any]]:
    """Fetches users for a particular semester, or ALL users if semester_id is None."""
    query = gql(
        """
        query semester_users($where: users_bool_exp!) {
            users(order_by: [
                { display_name:asc_nulls_last}, {email: asc_nulls_last}
            ], where: $where) {
                id
                display_name
                role
                email
                created_at
                rcs_id
                graduation_year
                github_username
                is_verified
                enrollments_aggregate {
                    aggregate {
                        count
                    }
                }
            }
        }
        """
    )

    where_clause: Dict[str, Any] = {}

    if semester_id:
        where_clause["enrollments"] = {"semester_id": {"_eq": semester_id}}

    result = client.execute(query, variable_values={"where": where_clause})
    return result["users"]


def get_semesters(client: Client) -> List[Dict[str, Any]]:
    """Fetches all semesters, ordered ascendingly by start date."""
    query = gql(
        """
        query semesters {
            semesters(order_by: {start_date: asc_nulls_last}) {
                id
                name
                type
                start_date
                end_date
                is_open_to_new_projects
            }
        }
        """
    )

    semesters = client.execute(query)["semesters"]
    return semesters


def get_project(client: Client, project_id: str) -> Optional[Dict[str, Any]]:
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
                        display_name
                    }
                    semester_id
                }
            }
        }
        """
    )

    result = client.execute(query, variable_values={"pid": project_id})
    return result["project"]


def get_enrollment(
    client: Client, user_id: str, semester_id: str
) -> Optional[Dict[str, Any]]:
    """Fetches a particular enrollment by user and semester IDs."""
    query = gql(
        """
        query get_enrollment($user_id: uuid!, $semester_id: String!) {
            enrollments(
                limit: 1,
                where: { user_id: { _eq: $user_id }, semester_id: { _eq: $semester_id } }
            ) {
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

    return enrollments[0]


def get_projects(
    client: Client,
    with_enrollments: bool,
    semester_id: Optional[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetches all projects in the current semester.
    Returns project name.
    """

    projects_where_exp = {}
    if semester_id:
        projects_where_exp = {"enrollments": {"semester_id": {"_eq": semester_id}}}

    enrollments_where_exp = {}
    if semester_id:
        enrollments_where_exp = {"semester_id": {"_eq": semester_id}}

    query = gql(
        """
        query SemesterProjects(
            $projects_where_exp: projects_bool_exp,
            $enrollments_where_exp: enrollments_bool_exp,
            $withEnrollments: Boolean!
        ) {
          projects(order_by: {name: asc}, where: $projects_where_exp) {
            id
            name
            tags
            github_repos
            short_description
            created_at
            is_approved
            project_leads: enrollments(where: {_and:
                [$enrollments_where_exp, {is_project_lead: {_eq:true}}]
            }) @include(if: $withEnrollments) {
                user_id
                user {
                    display_name
                }
            }
            enrollments_aggregate(where: $enrollments_where_exp) {
                aggregate {
                    count
                }
            }
            enrollments(where: $enrollments_where_exp) @include(if: $withEnrollments) {
                user {
                    id
                    display_name
                    graduation_year
                }
                is_project_lead
                credits
            }
            owner {
                id
                display_name
            }
          }
        }
    """
    )

    result = client.execute(
        query,
        variable_values={
            "projects_where_exp": projects_where_exp,
            "enrollments_where_exp": enrollments_where_exp,
            "withEnrollments": with_enrollments,
        },
    )

    return result["projects"]


def add_project(client: Client, project_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates new project with name=name and description=desc where owner is user that has id=owner_id
    """
    query = gql(
        """
        mutation AddProject($owner_id: uuid!, $project_data: projects_insert_input!) {
            insert_projects_one(object: $project_data) {
                id
            }
        }
    """
    )

    result = client.execute(
        query,
        variable_values={"project_data": project_data},
    )

    return result["insert_projects_one"]


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
            }
        }
        """
    )
    result = client.execute(query, variable_values={"where_clause": where_clause})
    return result["meetings"]


def get_meeting_by_id(client: Client, meeting_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a particular meeting by it's ID."""
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
                created_at
                host {
                    id
                    display_name
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


def add_project_lead(
    client: Client, project_id: str, user_id: str, semester_id: str, credit_count: int
):
    """
    Adds user with id=user_id as project lead of project with id=project_id.
    Also adds corresponding enrollment to current semester.
    """
    query = gql(
        """
        mutation AddProjectLead(
            $project_id: uuid!,
            $user_id: uuid!,
            $semester_id: String!,
            $credits: Int!
        ) {
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
            "credits": credit_count,
        },
    )

    return result["insert_enrollments_one"]


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

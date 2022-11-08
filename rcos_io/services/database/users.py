"""
This module contains database CRUD operations for users.
"""
from typing import Any, Dict, List, Optional, Tuple
from gql import Client, gql

from . import fragments


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


def find_user_by_email(client: Client, email: str):
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
        fragments.BASIC_USER_DATA_FRAGMENT_INLINE
        + """
        query find_user($email: String!) {
            users(limit: 1, where: {_or: [{email: {_eq: $email}}, {_and: [{is_secondary_email_verified: {_eq:true}, secondary_email: {_eq: $email}}]}]}) {
                ...basicUser
            }
        }
    """
    )

    users: List[Dict[str, Any]] = client.execute(
        query, variable_values={"email": email}
    )["users"]

    if len(users) == 0:
        return None

    return users[0]


def create_user_with_email(client: Client, email: str, role: str):
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
        fragments.BASIC_USER_DATA_FRAGMENT_INLINE
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

    user: Dict[str, Any] = client.execute(query, variable_values={"user": user_values})[
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
        fragments.BASIC_USER_DATA_FRAGMENT_INLINE
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


def find_user_by_rcs_id(
    client: Client, rcs_id: str, include_enrollments: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Fetches a user with the given RCS ID. Optionally includes their enrollments.

    Args:
        client: GQL client
        rcs_id: the RCS ID of the user to fetch
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

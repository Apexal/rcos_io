"""
This module contains database CRUD operations for projects.
"""
from typing import Any, Dict, List, Optional, Tuple
from gql import Client, gql


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

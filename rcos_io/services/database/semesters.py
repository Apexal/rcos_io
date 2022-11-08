"""
This module contains database CRUD operations for semesters.
"""
from typing import List, Dict, Any
from gql import Client, gql


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

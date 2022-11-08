"""
This package contains all database-related functionality.

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

from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from rcos_io.services import settings

# Import everything from all the modules in this package so that
# everything can be imported from rcos_io.services.database
# instead of having to import from each module
from .meetings import *
from .projects import *
from .users import *
from .semesters import *
from .attendance import *
from .small_group import *


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

"""
This modules defines the database blueprint. It exports all database required variables
and sets up database connections with Flask requests.
"""

from flask import Blueprint
from .models import db

bp = Blueprint("database", __name__)


@bp.before_app_request
def connect_db():
    """Makes a new connection to the database at the start of the request."""
    db.connect()


@bp.after_app_request
def close_db(response):
    """Closes the connection opened for the request at the end of the request."""
    db.close()
    return response

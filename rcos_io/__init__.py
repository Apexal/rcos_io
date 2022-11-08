"""
This module is the entry point to the application.

It creates the Flask app and registers the app blueprints
which handle the different routes, filters, and functionality of the app.
"""

from flask import Flask, render_template, g
from .services import filters, database, settings

# Import and register blueprints
# See https://flask.palletsprojects.com/en/2.2.x/blueprints/
from .blueprints import auth, meetings, users, projects, attendance

# Create and configure the app
app = Flask(__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY

# Add these environment variables to the config dictionary
# so we can access them in templates (config is accessible in all templates)
app.config["HASURA_CONSOLE_URL"] = settings.HASURA_CONSOLE_URL
app.config["RAILWAY_PROJECT_URL"] = settings.RAILWAY_PROJECT_URL


@app.before_request
def attach_db_client():
    """Creates a new GQL client and attach it to the every reqest as `g.db_client`."""
    g.db_client = database.client_factory()


# Temporary home route
@app.route("/")
def index():
    """Renders the index template."""
    return render_template("index.html")


# Register app blueprints
app.register_blueprint(filters.bp)
app.register_blueprint(auth.bp, url_prefix="/")
app.register_blueprint(projects.bp, url_prefix="/projects")
app.register_blueprint(meetings.bp, url_prefix="/meetings")
app.register_blueprint(users.bp, url_prefix="/users")
app.register_blueprint(attendance.bp, url_prefix="/attendance")
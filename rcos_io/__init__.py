"""
This module is the entry point to the application.

It creates the Flask app and registers the app blueprints
which handle the different routes, filters, and functionality of the app.
"""

from flask import Flask, render_template
from rcos_io import settings, filters
from rcos_io.services import db

# Import and register blueprints
# See https://flask.palletsprojects.com/en/2.2.x/blueprints/
from .views import auth
from .views import projects
from .views import meetings
from .views import members
from .views import attendance

# Create and configure the app
app = Flask(__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY

# Add these environment variables to the config dictionary
# so we can access them in templates (config is accessible in all templates)
app.config["HASURA_CONSOLE_URL"] = settings.HASURA_CONSOLE_URL
app.config["RAILWAY_PROJECT_URL"] = settings.RAILWAY_PROJECT_URL

# Temporary home route
@app.route("/")
def index():
    """Renders the index template."""
    return render_template("index.html")


# Register app blueprints
app.register_blueprint(db.bp)
app.register_blueprint(filters.bp)
app.register_blueprint(auth.bp)
app.register_blueprint(projects.bp)
app.register_blueprint(meetings.bp)
app.register_blueprint(members.bp)
app.register_blueprint(attendance.bp)

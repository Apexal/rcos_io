from flask import Flask, render_template
from rcos_io import settings

# Create and configure the app
app = Flask(__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY

# Add these environment variables to the config dictionary so we can access them in templates (config is accessible in all templates)
app.config["HASURA_CONSOLE_URL"] = settings.HASURA_CONSOLE_URL
app.config["RAILWAY_PROJECT_URL"] = settings.RAILWAY_PROJECT_URL

# Temporary home route
@app.route("/")
def index():
    return render_template("index.html")


# Import filters file to register them in Jinja
from . import filters

# Import and register blueprints
# See https://flask.palletsprojects.com/en/2.2.x/blueprints/
from .views import auth
from .views import projects
from .views import meetings
from .views import members
from .views import attendance

app.register_blueprint(auth.bp)
app.register_blueprint(projects.bp)
app.register_blueprint(meetings.bp)
app.register_blueprint(members.bp)
app.register_blueprint(attendance.bp)

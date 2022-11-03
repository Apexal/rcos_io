from flask import Flask, render_template
from rcos_io.settings import SECRET_KEY

# Create and configure the app
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

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

app.register_blueprint(auth.bp)
app.register_blueprint(projects.bp)
app.register_blueprint(meetings.bp)
app.register_blueprint(members.bp)

from typing import Dict
from dotenv import load_dotenv

from flask import Flask, render_template
import rcos_io.services.db
from rcos_io.settings import SECRET_KEY

load_dotenv()


def create_app():
    # Create and configure the app
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY

    # Temporary home route
    @app.route("/")
    def index():
        return render_template("index.html")

    from .views import auth
    from .views import projects
    from .views import meetings
    from .views import members

    app.register_blueprint(auth.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(meetings.bp)
    app.register_blueprint(members.bp)

    return app

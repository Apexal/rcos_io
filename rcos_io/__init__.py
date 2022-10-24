import os
from typing import Dict
from dotenv import load_dotenv

from flask import Flask, render_template
from rcos_io.auth import login_required
import rcos_io.db

load_dotenv()


def create_app(test_config: Dict[str, str | bool] | None = None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Temporary home route
    @app.route("/")
    def index():
        return render_template("index.html")

    # Route for testing log in
    @app.route("/secret")
    @login_required
    def secret():
        return "Hello logged in users!"

    from . import auth
    from .views import projects

    app.register_blueprint(auth.bp)
    app.register_blueprint(projects.bp)

    return app

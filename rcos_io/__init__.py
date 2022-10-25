from typing import Dict
from dotenv import load_dotenv

from flask import Flask, render_template
import rcos_io.db
from rcos_io.settings import SECRET_KEY

load_dotenv()


def create_app(test_config: Dict[str, str | bool] | None = None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = SECRET_KEY

    # Temporary home route
    @app.route("/")
    def index():
        return render_template("index.html")

    from .views import auth
    from .views import projects
    from .views import meetings

    app.register_blueprint(auth.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(meetings.bp)

    return app

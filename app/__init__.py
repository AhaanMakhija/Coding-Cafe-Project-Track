"""The ORBIT Flask application package."""

import os

from flask import Flask

from app.extensions import db
from config import Config


def create_app(config_class=Config):
    """Build and return a configured Flask app (the application factory).

    Args:
        config_class: Settings to load. Defaults to Config; tests pass TestConfig.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # SQLite cannot create the folder its database file lives in.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401  (registers the tables with db)

        db.create_all()

    # Temporary page to prove the app runs; replaced by Blueprints in Week 2.
    @app.route("/")
    def index():
        return "ORBIT is running."

    return app

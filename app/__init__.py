"""The ORBIT Flask application package."""

from flask import Flask

from config import Config


def create_app(config_class=Config):
    """Build and return a configured Flask app (the application factory).

    Args:
        config_class: Settings to load. Defaults to Config; tests pass TestConfig.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Temporary page to prove the app runs; replaced by Blueprints in Week 2.
    @app.route("/")
    def index():
        return "ORBIT is running."

    return app

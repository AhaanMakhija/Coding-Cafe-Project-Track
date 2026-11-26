"""The ORBIT Flask application package."""

import os

from flask import Flask, render_template

from app import demo, errors, template_filters
from app.extensions import csrf, db, login_manager
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
    login_manager.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401  (registers the tables with db)

        db.create_all()

    from app.admin import bp as admin_bp
    from app.auth import bp as auth_bp
    from app.calendar import bp as calendar_bp
    from app.forum import bp as forum_bp
    from app.resources import bp as resources_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(resources_bp, url_prefix="/courses")
    app.register_blueprint(calendar_bp, url_prefix="/calendar")
    app.register_blueprint(forum_bp, url_prefix="/board")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.route("/")
    def index():
        return render_template("index.html")

    template_filters.register(app)

    @app.context_processor
    def upload_limit():
        """Make the upload limit available to every template as max_upload_mb."""
        return {"max_upload_mb": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)}

    errors.register(app)
    demo.register(app)  # the `flask seed-demo` command

    @app.after_request
    def security_headers(response):
        """Extra browser protections added to every response."""
        # Never guess a file's type: an upload can't be treated as a script or page.
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Other sites can't show ORBIT inside a hidden frame to trick clicks (clickjacking).
        response.headers["X-Frame-Options"] = "DENY"
        # Links to other sites don't reveal which ORBIT page you came from.
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    return app

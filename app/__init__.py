"""The ORBIT Flask application package."""

import os

from flask import Flask, render_template, request, url_for

from app import template_filters
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

    from app.auth import bp as auth_bp
    from app.calendar import bp as calendar_bp
    from app.forum import bp as forum_bp
    from app.resources import bp as resources_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(resources_bp, url_prefix="/courses")
    app.register_blueprint(calendar_bp, url_prefix="/calendar")
    app.register_blueprint(forum_bp, url_prefix="/board")

    @app.route("/")
    def index():
        return render_template("index.html")

    template_filters.register(app)

    @app.context_processor
    def upload_limit():
        """Make the upload limit available to every template as max_upload_mb."""
        return {"max_upload_mb": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)}

    @app.errorhandler(413)
    def file_too_large(error):
        """Flask raises 413 when a request is bigger than MAX_CONTENT_LENGTH."""
        # If it happened on the add-resource form, offer the same form with
        # "Link" already selected so the user can paste a share link instead.
        link_form_url = None
        if request.endpoint == "resources.new_resource" and request.view_args:
            link_form_url = url_for(
                "resources.new_resource", course_id=request.view_args["course_id"], kind="link"
            )
        return render_template("errors/413.html", link_form_url=link_form_url), 413

    return app

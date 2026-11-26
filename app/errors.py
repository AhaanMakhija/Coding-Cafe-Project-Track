"""Friendly error pages, so visitors never see Flask's bare default pages."""

from flask import render_template, request, url_for
from flask_wtf.csrf import CSRFError

from app.extensions import db

# Status code -> (heading, explanation) shown on errors/error.html.
MESSAGES = {
    400: ("That request didn't make sense.", "Something in the link or form was not valid. Go back and try again."),
    403: ("You can't do that here.", "Your account doesn't have permission for this page or action."),
    404: ("We couldn't find that page.", "It may have been deleted, or the link may be mistyped."),
    405: ("That isn't allowed here.", "This page doesn't accept that kind of request."),
    500: ("Something went wrong on our side.", "The problem has been logged. Please try again in a moment."),
}


def render_error(code, heading=None, message=None):
    default_heading, default_message = MESSAGES.get(code, MESSAGES[500])
    return render_template(
        "errors/error.html", code=code,
        heading=heading or default_heading, message=message or default_message,
    ), code


def register(app):
    """Attach the error handlers to app. Called from create_app()."""

    for code in (400, 403, 404, 405):
        app.register_error_handler(code, lambda error, code=code: render_error(code))

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        # Usually the page was open so long that its form token expired.
        return render_error(400, "This form expired.",
                            "For your security, forms expire after a while. Go back, reload the page and submit again.")

    @app.errorhandler(500)
    def server_error(error):
        # Undo any half-finished database change so the next request starts clean.
        db.session.rollback()
        return render_error(500)

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

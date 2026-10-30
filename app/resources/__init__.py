"""Resources Blueprint: courses, enrollment and each course's resource library."""

from flask import Blueprint

bp = Blueprint("resources", __name__)

from app.resources import routes  # noqa: E402,F401  (attaches the routes to bp)

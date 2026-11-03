"""Calendar Blueprint: campus events, your weekly classes, and the merged calendar."""

from flask import Blueprint

bp = Blueprint("calendar", __name__)

from app.calendar import routes  # noqa: E402,F401  (attaches the routes to bp)

"""Resources Blueprint: courses, enrollment and each course's resource library."""

from flask import Blueprint

from app.resources.links import link_source

bp = Blueprint("resources", __name__)

# Lets templates write {{ resource.url | link_source }} -> "Google Drive".
bp.add_app_template_filter(link_source, "link_source")

from app.resources import routes  # noqa: E402,F401  (attaches the routes to bp)

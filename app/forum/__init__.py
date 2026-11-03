"""Forum Blueprint: one discussion board per course, with threads, replies and attachments."""

from flask import Blueprint

bp = Blueprint("forum", __name__)

from app.forum import routes  # noqa: E402,F401  (attaches the routes to bp)

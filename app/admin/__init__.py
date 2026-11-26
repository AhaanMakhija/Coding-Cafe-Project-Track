"""Admin Blueprint: see every account and change its details. Admins only."""

from flask import Blueprint

bp = Blueprint("admin", __name__)

from app.admin import routes  # noqa: E402,F401  (attaches the routes to bp)

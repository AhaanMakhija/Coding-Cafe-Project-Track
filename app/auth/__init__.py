"""Accounts Blueprint: sign up, log in, log out and the profile page."""

from flask import Blueprint

bp = Blueprint("auth", __name__)

from app.auth import routes  # noqa: E402,F401  (attaches the routes to bp)

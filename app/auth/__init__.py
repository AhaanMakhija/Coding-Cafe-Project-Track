"""Accounts Blueprint: sign up, log in, log out, profile and account commands."""

from flask import Blueprint

# cli_group=None puts this Blueprint's commands at the top level:
# `flask make-staff`, not `flask auth make-staff`.
bp = Blueprint("auth", __name__, cli_group=None)

from app.auth import commands, routes  # noqa: E402,F401  (attaches them to bp)

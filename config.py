"""Configuration classes for ORBIT.

create_app() takes one of these classes, so the same code can run with
development settings or with test settings without any edits.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Default settings used when running the app locally."""

    # Signs session cookies and protects forms (CSRF). Read from the
    # environment in production; the fallback is only for local development.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # One SQLite file in the instance/ folder (git-ignored).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "orbit.db")
    )

    # Uploaded files are stored on disk here, never in the database.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # Flask rejects any request body larger than this (10 MB) before our code runs.
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024


class TestConfig(Config):
    """Settings for pytest: an in-memory database that vanishes after each test."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

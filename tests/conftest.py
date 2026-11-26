"""Shared pytest fixtures: every test gets a fresh app built with TestConfig."""

import pytest
from flask import g
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import User
from config import TestConfig

TEST_PASSWORD = "correct-horse"


class CookieOnlyClient(FlaskClient):
    """A test client that finds the logged-in user from the session cookie on every request.

    The app fixture keeps one app context open for the whole test, and Flask-Login
    caches the current user in `g` on that context. Without clearing it, requests
    after log_in() would reuse the cached user and never test the real path a
    browser takes: cookie -> load_user() -> User.
    """

    def open(self, *args, **kwargs):
        g.pop("_login_user", None)
        return super().open(*args, **kwargs)


@pytest.fixture
def app(tmp_path):
    """A fresh app with empty tables; everything is wiped after the test.

    Uploads go to pytest's temporary folder, never the real uploads/ folder.
    """
    app = create_app(TestConfig)
    app.test_client_class = CookieOnlyClient
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()  # close the SQLite connection (avoids ResourceWarning)


@pytest.fixture
def client(app):
    """A fake browser that sends requests to the app without starting a server."""
    return app.test_client()


@pytest.fixture
def make_user(app):
    """Factory fixture: call make_user(...) inside a test to save a user."""

    def _make_user(email="student@plaksha.edu.in", role="student", name="Sam Student"):
        user = User(name=name, email=email, role=role)
        user.set_password(TEST_PASSWORD)
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


def log_in(client, user):
    """Log the test client in as user."""
    response = client.post("/auth/login", data={"email": user.email, "password": TEST_PASSWORD})
    assert response.status_code == 302, "test login failed"

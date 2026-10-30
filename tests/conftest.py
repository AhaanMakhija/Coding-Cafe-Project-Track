"""Shared pytest fixtures: every test gets a fresh app built with TestConfig."""

import pytest

from app import create_app
from app.extensions import db
from app.models import User
from config import TestConfig

TEST_PASSWORD = "correct-horse"


@pytest.fixture
def app(tmp_path):
    """A fresh app with empty tables; everything is wiped after the test.

    Uploads go to pytest's temporary folder, never the real uploads/ folder.
    """
    app = create_app(TestConfig)
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


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

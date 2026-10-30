"""Shared pytest fixtures: every test gets a fresh app built with TestConfig."""

import pytest

from app import create_app
from app.extensions import db
from config import TestConfig


@pytest.fixture
def app():
    """A fresh app with empty tables; everything is wiped after the test."""
    app = create_app(TestConfig)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A fake browser that sends requests to the app without starting a server."""
    return app.test_client()

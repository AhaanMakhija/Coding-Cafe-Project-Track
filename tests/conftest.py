"""Shared pytest fixtures: every test gets a fresh app built with TestConfig."""

import pytest

from app import create_app
from config import TestConfig


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    """A fake browser that sends requests to the app without starting a server."""
    return app.test_client()

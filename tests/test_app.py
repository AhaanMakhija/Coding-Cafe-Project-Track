"""Tests for the application factory itself."""

import pytest


def test_app_uses_test_config(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_upload_limit_is_10_mb(app):
    assert app.config["MAX_CONTENT_LENGTH"] == 10 * 1024 * 1024


@pytest.mark.parametrize("count, args, expected", [
    (1, ("file",), "1 file"),
    (0, ("file",), "0 files"),
    (3, ("file",), "3 files"),
    (1, ("weekly class", "weekly classes"), "1 weekly class"),
    (2, ("weekly class", "weekly classes"), "2 weekly classes"),
])
def test_plural_filter(app, count, args, expected):
    assert app.jinja_env.filters["plural"](count, *args) == expected


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Organized Resources, Boards, Info &amp; Timetable" in response.data

"""Tests for the application factory itself."""


def test_app_uses_test_config(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_upload_limit_is_10_mb(app):
    assert app.config["MAX_CONTENT_LENGTH"] == 10 * 1024 * 1024


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ORBIT is running." in response.data

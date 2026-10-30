"""Tests for the `flask make-staff` command."""

import pytest

from app.extensions import db
from app.models import User


@pytest.fixture
def runner(app):
    """Runs Flask CLI commands inside the test app."""
    return app.test_cli_runner()


@pytest.fixture
def student(app):
    user = User(name="Sam Student", email="student@plaksha.edu.in")
    user.set_password("correct-horse")
    db.session.add(user)
    db.session.commit()
    return user


def test_make_staff_promotes_student(runner, student):
    result = runner.invoke(args=["make-staff", "student@plaksha.edu.in"])
    assert result.exit_code == 0
    assert "is now staff" in result.output
    assert student.role == "staff"


def test_make_staff_email_is_case_insensitive(runner, student):
    result = runner.invoke(args=["make-staff", "Student@PLAKSHA.edu.in"])
    assert result.exit_code == 0
    assert student.is_staff


def test_make_staff_unknown_email_fails(runner, student):
    result = runner.invoke(args=["make-staff", "nobody@plaksha.edu.in"])
    assert result.exit_code == 1
    assert "No account found" in result.output
    assert student.role == "student"


def test_make_staff_twice_is_harmless(runner, student):
    runner.invoke(args=["make-staff", "student@plaksha.edu.in"])
    result = runner.invoke(args=["make-staff", "student@plaksha.edu.in"])
    assert result.exit_code == 0
    assert "already staff" in result.output


def test_staff_role_shows_on_profile(app, runner, student):
    runner.invoke(args=["make-staff", "student@plaksha.edu.in"])
    client = app.test_client()
    client.post("/auth/login", data={"email": "student@plaksha.edu.in", "password": "correct-horse"})
    assert b"Staff" in client.get("/auth/profile").data

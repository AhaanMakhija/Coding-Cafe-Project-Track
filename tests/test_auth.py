"""Tests for the accounts Blueprint: sign up, log in, log out and profile."""

import pytest

from app.auth.routes import is_safe_next_url
from app.extensions import db
from app.models import User

PASSWORD = "correct-horse"


def signup(client, email="new@plaksha.edu.in", password=PASSWORD, confirm=None, name="New User"):
    return client.post("/auth/signup", data={
        "name": name, "email": email, "password": password,
        "confirm": confirm if confirm is not None else password,
    })


def login(client, email="student@plaksha.edu.in", password=PASSWORD, next_url=None):
    url = "/auth/login" + (f"?next={next_url}" if next_url else "")
    return client.post(url, data={"email": email, "password": password})


@pytest.fixture
def student(app):
    user = User(name="Sam Student", email="student@plaksha.edu.in")
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


# --- Sign up ----------------------------------------------------------------

def test_signup_page_loads(client):
    assert client.get("/auth/signup").status_code == 200


def test_signup_creates_student_and_logs_in(client):
    response = signup(client, email="New@Plaksha.edu.in")
    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/profile"

    user = db.session.scalar(db.select(User).filter_by(email="new@plaksha.edu.in"))
    assert user is not None
    assert user.role == "student"
    assert user.password_hash != PASSWORD

    assert b"New User" in client.get("/auth/profile").data  # already logged in


def test_signup_rejects_duplicate_email(client, student):
    response = signup(client, email="STUDENT@plaksha.edu.in")
    assert response.status_code == 200  # form shown again
    assert b"already exists" in response.data
    assert db.session.query(User).count() == 1


@pytest.mark.parametrize("fields, message", [
    ({"password": "short", "confirm": "short"}, b"at least 8 characters"),
    ({"confirm": "different-password"}, b"Passwords must match"),
    ({"email": "not-an-email"}, b"Invalid email address"),
    ({"name": ""}, b"This field is required"),
])
def test_signup_rejects_bad_input(client, fields, message):
    response = signup(client, **fields)
    assert response.status_code == 200
    assert message in response.data
    assert db.session.query(User).count() == 0


def test_signup_cannot_choose_staff_role(client):
    client.post("/auth/signup", data={
        "name": "Sneaky", "email": "sneaky@plaksha.edu.in",
        "password": PASSWORD, "confirm": PASSWORD, "role": "staff",
    })
    user = db.session.scalar(db.select(User).filter_by(email="sneaky@plaksha.edu.in"))
    assert user.role == "student"


# --- Log in -----------------------------------------------------------------

def test_login_success_goes_to_profile(client, student):
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/profile"


def test_login_email_is_case_insensitive(client, student):
    assert login(client, email="  Student@PLAKSHA.edu.in").status_code == 302


@pytest.mark.parametrize("email, password", [
    ("student@plaksha.edu.in", "wrong-password"),
    ("nobody@plaksha.edu.in", PASSWORD),
])
def test_login_failure_gives_same_message(client, student, email, password):
    response = login(client, email=email, password=password)
    assert response.status_code == 401
    assert b"Incorrect email or password." in response.data


def test_login_follows_safe_next_url(client, student):
    response = login(client, next_url="/auth/profile")
    assert response.headers["Location"] == "/auth/profile"


def test_login_ignores_external_next_url(client, student):
    response = login(client, next_url="https://evil.example/phish")
    assert response.headers["Location"] == "/auth/profile"


@pytest.mark.parametrize("target, safe", [
    ("/auth/profile", True),
    ("https://evil.example", False),
    ("//evil.example", False),
    ("profile", False),
    ("", False),
    (None, False),
])
def test_is_safe_next_url(target, safe):
    assert is_safe_next_url(target) is safe


# --- Profile and log out ------------------------------------------------------

def test_profile_requires_login(client):
    response = client.get("/auth/profile")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")


def test_profile_shows_user_details(client, student):
    login(client)
    page = client.get("/auth/profile").data
    assert b"Sam Student" in page
    assert b"student@plaksha.edu.in" in page
    assert b"haven't joined any courses" in page


def test_logout_ends_session(client, student):
    login(client)
    response = client.post("/auth/logout")
    assert response.status_code == 302
    assert client.get("/auth/profile").status_code == 302  # back to login


def test_logout_rejects_get(client, student):
    login(client)
    assert client.get("/auth/logout").status_code == 405

"""Tests for admin sign-up and the admin pages."""

import pytest

from app.extensions import db
from app.models import Course, User
from conftest import TEST_PASSWORD, log_in

SIGNUP = {"name": "Ada Admin", "email": "ada@plaksha.edu.in", "password": "long-enough-pw",
          "confirm": "long-enough-pw"}


@pytest.fixture
def admin(make_user):
    return make_user(email="admin@plaksha.edu.in", role="admin", name="Ada Admin")


@pytest.fixture
def student(make_user):
    return make_user()


def edit(client, user, **overrides):
    data = {"name": user.name, "email": user.email, "role": user.role, "new_password": ""}
    data.update(overrides)
    return client.post(f"/admin/users/{user.id}", data=data)


# --- Signing up as admin -------------------------------------------------------------

def test_signup_with_the_admin_code_makes_an_admin(client):
    response = client.post("/auth/signup", data={**SIGNUP, "account_type": "admin", "admin_code": "admin"})
    assert response.status_code == 302
    assert db.session.scalar(db.select(User)).role == "admin"


@pytest.mark.parametrize("code", ["", "Admin", "admin ", "wrong"])
def test_wrong_admin_code_is_rejected(client, code):
    response = client.post("/auth/signup", data={**SIGNUP, "account_type": "admin", "admin_code": code})
    assert b"That admin code is not right." in response.data
    assert db.session.scalar(db.select(User)) is None


def test_admin_code_comes_from_config(app, client):
    app.config["ADMIN_SIGNUP_CODE"] = "a-long-real-secret"
    response = client.post("/auth/signup", data={**SIGNUP, "account_type": "admin", "admin_code": "admin"})
    assert b"That admin code is not right." in response.data
    client.post("/auth/signup", data={**SIGNUP, "account_type": "admin", "admin_code": "a-long-real-secret"})
    assert db.session.scalar(db.select(User)).is_admin


def test_student_signup_ignores_the_admin_code_box(client):
    client.post("/auth/signup", data={**SIGNUP, "account_type": "student", "admin_code": "anything"})
    assert db.session.scalar(db.select(User)).role == "student"


def test_signup_without_account_type_is_a_student(client):
    client.post("/auth/signup", data=SIGNUP)
    assert db.session.scalar(db.select(User)).role == "student"


def test_made_up_account_type_is_rejected(client):
    response = client.post("/auth/signup", data={**SIGNUP, "account_type": "staff", "admin_code": "admin"})
    assert b"Not a valid choice" in response.data
    assert db.session.scalar(db.select(User)) is None


def test_signup_page_has_the_switch(client):
    page = client.get("/auth/signup").get_data(as_text=True)
    assert 'value="admin"' in page and "Admin code" in page


# --- Who can open the admin pages ---------------------------------------------------

def test_admin_pages_need_login(client):
    assert client.get("/admin/").status_code == 302


@pytest.mark.parametrize("role", ["student", "staff"])
def test_non_admins_get_403(client, make_user, role):
    user = make_user(role=role)
    log_in(client, user)
    assert client.get("/admin/").status_code == 403
    assert client.get(f"/admin/users/{user.id}").status_code == 403
    assert edit(client, user, role="admin").status_code == 403
    assert user.role == role


def test_admin_link_only_for_admins(client, admin, student):
    log_in(client, student)
    assert b'href="/admin/"' not in client.get("/").data
    client.post("/auth/logout")
    log_in(client, admin)
    assert b'href="/admin/"' in client.get("/").data


def test_admin_has_staff_powers(client, admin):
    log_in(client, admin)
    assert client.get("/courses/new").status_code == 200


# --- Seeing accounts ------------------------------------------------------------------

def test_admin_sees_every_account(client, admin, student, make_user):
    course = Course(code="CS101", name="Intro", term="Fall 2026")
    student.courses.append(course)
    make_user(email="prof@plaksha.edu.in", role="staff", name="Prof Staff")
    db.session.commit()
    log_in(client, admin)

    page = client.get("/admin/").get_data(as_text=True)
    for text in ("Ada Admin", "Sam Student", "Prof Staff", "student@plaksha.edu.in", "CS101"):
        assert text in page
    assert "1 student · 1 staff · 1 admin" in page


def test_staff_count_is_not_pluralised_as_staffs(client, admin, make_user):
    make_user(email="a@plaksha.edu.in", role="staff")
    make_user(email="b@plaksha.edu.in", role="staff")
    log_in(client, admin)
    page = client.get("/admin/").get_data(as_text=True)
    assert "2 staff" in page and "staffs" not in page


def test_admin_search_and_role_filter(client, admin, student, make_user):
    make_user(email="prof@plaksha.edu.in", role="staff", name="Prof Staff")
    log_in(client, admin)
    page = client.get("/admin/?q=prof").get_data(as_text=True)
    assert "Prof Staff" in page and "Sam Student" not in page
    page = client.get("/admin/?role=student").get_data(as_text=True)
    assert "Sam Student" in page and "Prof Staff" not in page


def test_details_page_shows_activity_but_never_the_password(client, admin, student):
    log_in(client, admin)
    page = client.get(f"/admin/users/{student.id}").get_data(as_text=True)
    assert "Sam Student" in page and "Replies posted" in page
    assert student.password_hash not in page
    assert TEST_PASSWORD not in page


def test_unknown_account_is_404(client, admin):
    log_in(client, admin)
    assert client.get("/admin/users/999").status_code == 404


# --- Changing accounts ---------------------------------------------------------------

def test_admin_changes_name_email_and_role(client, admin, student):
    log_in(client, admin)
    response = edit(client, student, name="Sam S.", email="SAM@plaksha.edu.in", role="staff")
    assert response.status_code == 302
    assert (student.name, student.email, student.role) == ("Sam S.", "sam@plaksha.edu.in", "staff")


def test_admin_sets_a_new_password_that_works(client, admin, student):
    log_in(client, admin)
    edit(client, student, new_password="brand-new-pass")
    client.post("/auth/logout")
    response = client.post("/auth/login", data={"email": student.email, "password": "brand-new-pass"})
    assert response.status_code == 302


def test_empty_password_box_keeps_the_old_password(client, admin, student):
    log_in(client, admin)
    old_hash = student.password_hash
    edit(client, student, name="Renamed")
    assert student.password_hash == old_hash


def test_short_new_password_is_rejected(client, admin, student):
    log_in(client, admin)
    response = edit(client, student, new_password="short")
    assert b"at least 8 characters" in response.data


def test_email_already_used_is_rejected(client, admin, student):
    log_in(client, admin)
    response = edit(client, student, email=admin.email)
    assert b"Another account already uses this email." in response.data
    assert student.email == "student@plaksha.edu.in"


def test_keeping_your_own_email_is_fine(client, admin, student):
    log_in(client, admin)
    assert edit(client, student, name="Same email").status_code == 302


def test_last_admin_cannot_be_demoted(client, admin):
    log_in(client, admin)
    response = edit(client, admin, role="student")
    assert b"This is the only admin." in response.data
    assert admin.role == "admin"


def test_an_admin_can_be_demoted_when_another_exists(client, admin, make_user):
    other = make_user(email="other-admin@plaksha.edu.in", role="admin", name="Other Admin")
    log_in(client, admin)
    assert edit(client, other, role="staff").status_code == 302
    assert other.role == "staff"


def test_made_up_role_is_rejected(client, admin, student):
    log_in(client, admin)
    response = edit(client, student, role="superuser")
    assert b"Not a valid choice" in response.data
    assert student.role == "student"

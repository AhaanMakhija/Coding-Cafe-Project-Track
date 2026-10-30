"""Tests for courses, enrollment and the staff_required decorator."""

import pytest

from app.extensions import db
from app.models import Course
from conftest import log_in


@pytest.fixture
def student(make_user):
    return make_user()


@pytest.fixture
def staff(make_user):
    return make_user(email="staff@plaksha.edu.in", role="staff", name="Prof Staff")


@pytest.fixture
def course(app):
    course = Course(code="CS101", name="Intro to Programming", term="Fall 2026")
    db.session.add(course)
    db.session.commit()
    return course


def create_course(client, code="cs101 ", name="Intro to Programming", term="Fall 2026"):
    return client.post("/courses/new", data={"code": code, "name": name, "term": term})


# --- Who can see what --------------------------------------------------------

@pytest.mark.parametrize("url", ["/courses/", "/courses/new", "/courses/1"])
def test_course_pages_require_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")


def test_student_cannot_create_course(client, student):
    log_in(client, student)
    assert client.get("/courses/new").status_code == 403
    assert create_course(client).status_code == 403
    assert db.session.query(Course).count() == 0


def test_student_sees_no_new_course_button(client, student):
    log_in(client, student)
    assert b"New course" not in client.get("/courses/").data


def test_missing_course_is_404(client, student):
    log_in(client, student)
    assert client.get("/courses/999").status_code == 404
    assert client.post("/courses/999/join").status_code == 404


# --- Creating courses ---------------------------------------------------------

def test_staff_creates_course(client, staff):
    log_in(client, staff)
    response = create_course(client)
    assert response.status_code == 302

    course = db.session.scalar(db.select(Course))
    assert course.code == "CS101"  # trimmed and upper-cased
    assert response.headers["Location"] == f"/courses/{course.id}"
    assert b"CS101" in client.get("/courses/").data


def test_duplicate_course_in_same_term_is_rejected(client, staff, course):
    log_in(client, staff)
    response = create_course(client, code="CS101", term="Fall 2026")
    assert response.status_code == 200
    assert b"already exists" in response.data
    assert db.session.query(Course).count() == 1


def test_same_code_in_another_term_is_allowed(client, staff, course):
    log_in(client, staff)
    assert create_course(client, code="CS101", term="Spring 2027").status_code == 302
    assert db.session.query(Course).count() == 2


def test_course_form_requires_all_fields(client, staff):
    log_in(client, staff)
    response = create_course(client, code="", name="", term="")
    assert response.status_code == 200
    assert response.data.count(b"This field is required") == 3


# --- Joining and leaving ------------------------------------------------------

def test_join_course(client, student, course):
    log_in(client, student)
    response = client.post(f"/courses/{course.id}/join")
    assert response.status_code == 302
    assert course in student.courses
    assert b"CS101" in client.get("/auth/profile").data


def test_join_twice_does_not_duplicate(client, student, course):
    log_in(client, student)
    client.post(f"/courses/{course.id}/join")
    client.post(f"/courses/{course.id}/join")
    assert student.courses.count(course) == 1


def test_leave_course(client, student, course):
    log_in(client, student)
    client.post(f"/courses/{course.id}/join")
    client.post(f"/courses/{course.id}/leave")
    assert course not in student.courses


def test_leave_course_not_joined_is_harmless(client, student, course):
    log_in(client, student)
    assert client.post(f"/courses/{course.id}/leave").status_code == 302


def test_join_rejects_get(client, student, course):
    log_in(client, student)
    assert client.get(f"/courses/{course.id}/join").status_code == 405


def test_detail_page_shows_join_or_leave(client, student, course):
    log_in(client, student)
    assert b"Join course" in client.get(f"/courses/{course.id}").data
    client.post(f"/courses/{course.id}/join")
    page = client.get(f"/courses/{course.id}").data
    assert b"Leave course" in page
    assert b"1 enrolled" in page

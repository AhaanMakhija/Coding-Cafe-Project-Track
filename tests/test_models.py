"""Tests for the User, Course and enrollment tables."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Course, User


def make_user(email="student@plaksha.edu.in", role="student"):
    user = User(name="Test User", email=email, role=role)
    user.set_password("correct-horse")
    return user


def test_password_is_hashed_not_stored(app):
    user = make_user()
    assert user.password_hash != "correct-horse"
    assert user.check_password("correct-horse")
    assert not user.check_password("wrong-password")


def test_email_is_stored_lower_case(app):
    user = make_user(email="  Ahaan@Plaksha.EDU.in ")
    assert user.email == "ahaan@plaksha.edu.in"


def test_invalid_role_is_rejected(app):
    with pytest.raises(ValueError):
        make_user(role="admin")


def test_is_staff(app):
    assert make_user(role="staff").is_staff
    assert not make_user(role="student").is_staff


def test_duplicate_email_is_rejected(app):
    db.session.add(make_user(email="same@plaksha.edu.in"))
    db.session.commit()
    db.session.add(make_user(email="SAME@plaksha.edu.in"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_same_course_code_twice_in_one_term_is_rejected(app):
    db.session.add(Course(code="CS101", name="Intro", term="Fall 2026"))
    db.session.add(Course(code="CS101", name="Intro", term="Fall 2026"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_enrollment_links_both_ways(app):
    user = make_user()
    course = Course(code="CS101", name="Intro to Programming", term="Fall 2026")
    user.courses.append(course)
    db.session.add(user)
    db.session.commit()

    assert course in user.courses
    assert user in course.students

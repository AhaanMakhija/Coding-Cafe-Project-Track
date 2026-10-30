"""Tests for the Resource, Event and ClassSlot tables."""

from datetime import datetime, time

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ClassSlot, Course, Event, Resource, User


@pytest.fixture
def user_and_course(app):
    """A saved student and course for the new tables to point at."""
    user = User(name="Test User", email="student@plaksha.edu.in")
    user.set_password("correct-horse")
    course = Course(code="CS101", name="Intro to Programming", term="Fall 2026")
    db.session.add_all([user, course])
    db.session.commit()
    return user, course


# --- Resource ---------------------------------------------------------------

def test_file_resource_saves(user_and_course):
    user, course = user_and_course
    resource = Resource(title="Week 1 notes", kind="file", file_path="uploads/w1.pdf",
                        type="notes", course=course, uploader=user)
    db.session.add(resource)
    db.session.commit()

    assert resource in course.resources
    assert resource in user.resources
    assert resource.is_official is False  # student uploads are unofficial by default
    assert resource.created_at is not None


def test_link_resource_saves(user_and_course):
    user, course = user_and_course
    db.session.add(Resource(title="Drive folder", kind="link", url="https://drive.google.com/x",
                            course=course, uploader=user))
    db.session.commit()


@pytest.mark.parametrize("fields", [
    {"kind": "file"},                                            # file with no path
    {"kind": "link"},                                            # link with no URL
    {"kind": "file", "file_path": "a.pdf", "url": "https://x"},  # both at once
])
def test_resource_must_be_exactly_a_file_or_a_link(user_and_course, fields):
    user, course = user_and_course
    db.session.add(Resource(title="Bad", course=course, uploader=user, **fields))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_invalid_kind_and_type_are_rejected(app):
    with pytest.raises(ValueError):
        Resource(kind="video")
    with pytest.raises(ValueError):
        Resource(type="meme")


def test_tag_list_cleans_up_tags(app):
    resource = Resource(tags="Midterm, week 3 , ,PYTHON")
    assert resource.tag_list == ["midterm", "week 3", "python"]


def test_empty_tags_give_empty_list(app):
    assert Resource(tags="").tag_list == []


# --- Event ------------------------------------------------------------------

def test_event_saves(user_and_course):
    user, _ = user_and_course
    event = Event(title="Hackathon", start_at=datetime(2026, 11, 7, 10),
                  end_at=datetime(2026, 11, 7, 18), location="Main hall", creator=user)
    db.session.add(event)
    db.session.commit()
    assert event.creator == user


def test_event_cannot_end_before_it_starts(user_and_course):
    user, _ = user_and_course
    db.session.add(Event(title="Backwards", start_at=datetime(2026, 11, 7, 18),
                         end_at=datetime(2026, 11, 7, 10), creator=user))
    with pytest.raises(IntegrityError):
        db.session.commit()


# --- ClassSlot --------------------------------------------------------------

def test_class_slot_saves(user_and_course):
    user, course = user_and_course
    slot = ClassSlot(weekday=0, start_time=time(10, 0), end_time=time(11, 30),
                     room="204", user=user, course=course)
    db.session.add(slot)
    db.session.commit()
    assert slot in user.class_slots
    assert slot in course.class_slots


@pytest.mark.parametrize("weekday, start, end", [
    (7, time(10, 0), time(11, 0)),    # no eighth day of the week
    (-1, time(10, 0), time(11, 0)),
    (2, time(11, 0), time(10, 0)),    # ends before it starts
    (2, time(10, 0), time(10, 0)),    # zero length
])
def test_invalid_class_slots_are_rejected(user_and_course, weekday, start, end):
    user, course = user_and_course
    db.session.add(ClassSlot(weekday=weekday, start_time=start, end_time=end,
                             user=user, course=course))
    with pytest.raises(IntegrityError):
        db.session.commit()

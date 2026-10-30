"""Tests for the Thread and Post tables."""

from datetime import datetime

import pytest

from app.extensions import db
from app.models import Course, Post, Resource, Thread, User


@pytest.fixture
def user_and_course(app):
    user = User(name="Test User", email="student@plaksha.edu.in")
    user.set_password("correct-horse")
    course = Course(code="CS101", name="Intro to Programming", term="Fall 2026")
    db.session.add_all([user, course])
    db.session.commit()
    return user, course


def make_thread(user, course, title="Help with lab 2", created_at=None):
    thread = Thread(title=title, body="Stuck on question 3.", course=course, author=user)
    if created_at:
        thread.created_at = created_at
    db.session.add(thread)
    return thread


def test_thread_with_replies(user_and_course):
    user, course = user_and_course
    thread = make_thread(user, course)
    thread.posts.append(Post(body="Try a loop.", author=user))
    thread.posts.append(Post(body="Thanks!", author=user))
    db.session.commit()

    assert thread.reply_count == 2
    assert thread in course.threads
    assert all(post.attachment is None for post in thread.posts)  # attachments are optional


def test_new_thread_has_no_replies(user_and_course):
    user, course = user_and_course
    thread = make_thread(user, course)
    db.session.commit()
    assert thread.reply_count == 0


def test_course_threads_are_newest_first(user_and_course):
    user, course = user_and_course
    make_thread(user, course, "Old", created_at=datetime(2026, 10, 1))
    make_thread(user, course, "New", created_at=datetime(2026, 10, 20))
    make_thread(user, course, "Middle", created_at=datetime(2026, 10, 10))
    db.session.commit()
    db.session.expire(course)  # reload the list from the database

    assert [t.title for t in course.threads] == ["New", "Middle", "Old"]


def test_replies_are_oldest_first(user_and_course):
    user, course = user_and_course
    thread = make_thread(user, course)
    db.session.add_all([
        Post(body="second", author=user, thread=thread, created_at=datetime(2026, 10, 2)),
        Post(body="first", author=user, thread=thread, created_at=datetime(2026, 10, 1)),
    ])
    db.session.commit()
    db.session.expire(thread)

    assert [p.body for p in thread.posts] == ["first", "second"]


def test_deleting_thread_deletes_its_replies(user_and_course):
    user, course = user_and_course
    thread = make_thread(user, course)
    thread.posts.append(Post(body="reply", author=user))
    db.session.commit()

    db.session.delete(thread)
    db.session.commit()
    assert db.session.query(Post).count() == 0


def test_post_can_attach_a_resource(user_and_course):
    user, course = user_and_course
    file = Resource(title="My attempt", kind="file", file_path="uploads/lab2.py",
                    course=course, uploader=user)
    thread = make_thread(user, course)
    post = Post(body="Here is my code", author=user, thread=thread, attachment=file)
    db.session.add(post)
    db.session.commit()

    assert post.attachment.file_path == "uploads/lab2.py"

"""Tests for the course boards: threads, replies, attachments and deleting."""

import io
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models import Course, Post, Resource, Thread
from app.template_filters import timeago
from conftest import log_in

PDF_BYTES = b"%PDF-1.4 fake pdf for tests"


@pytest.fixture
def course(app):
    course = Course(code="CS101", name="Intro to Programming", term="Fall 2026")
    db.session.add(course)
    db.session.commit()
    return course


@pytest.fixture
def student(make_user, course):
    """A student already enrolled in CS101."""
    user = make_user()
    user.courses.append(course)
    db.session.commit()
    return user


@pytest.fixture
def other_student(make_user, course):
    """A second enrolled student, used to check people can't delete each other's posts."""
    user = make_user(email="other@plaksha.edu.in", name="Olly Other")
    user.courses.append(course)
    db.session.commit()
    return user


@pytest.fixture
def outsider(make_user):
    """A student who has not joined CS101."""
    return make_user(email="outsider@plaksha.edu.in", name="Ola Outsider")


@pytest.fixture
def staff(make_user):
    return make_user(email="staff@plaksha.edu.in", role="staff", name="Prof Staff")


@pytest.fixture
def thread(student, course):
    thread = Thread(title="Lab 2 question 3", body="Why does my loop never end?",
                    course=course, author=student)
    db.session.add(thread)
    db.session.commit()
    return thread


def start_thread(client, course, **overrides):
    data = {"title": "Lab 2 question 3", "body": "Why does my loop never end?"}
    data.update(overrides)
    return client.post(f"/board/{course.id}/new", data=data)


def post_reply(client, thread, body="Check your loop condition.", file=None):
    data = {"body": body}
    if file:
        data["file"] = (io.BytesIO(file[1]), file[0])
    return client.post(f"/board/threads/{thread.id}/reply", data=data,
                       content_type="multipart/form-data")


def uploaded_files(app):
    folder = app.config["UPLOAD_FOLDER"]
    return os.listdir(folder) if os.path.isdir(folder) else []


# --- Viewing ----------------------------------------------------------------------

def test_board_needs_login(client, course):
    response = client.get(f"/board/{course.id}/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_board_lists_threads_with_reply_counts(client, student, thread):
    db.session.add(Post(body="Same problem here", thread=thread, author=student))
    db.session.commit()
    log_in(client, student)

    page = client.get(f"/board/{thread.course_id}/").get_data(as_text=True)
    assert "Lab 2 question 3" in page
    assert "<strong>1</strong> reply" in page
    assert "1 thread" in page


def test_unknown_board_and_thread_are_404(client, student):
    log_in(client, student)
    assert client.get("/board/999/").status_code == 404
    assert client.get("/board/threads/999").status_code == 404


def test_course_page_links_to_its_board(client, student, course, thread):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}").get_data(as_text=True)
    assert f"/board/{course.id}/" in page
    assert "Board · 1 thread" in page


def test_outsider_can_read_but_sees_join_prompt(client, outsider, thread):
    log_in(client, outsider)
    page = client.get(f"/board/threads/{thread.id}").get_data(as_text=True)
    assert "Why does my loop never end?" in page
    assert "Join CS101 to reply." in page
    assert 'id="reply"' not in page


def test_thread_body_is_escaped(client, student, course):
    log_in(client, student)
    start_thread(client, course, body="<script>alert(1)</script>")
    page = client.get("/board/threads/1").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_staff_author_gets_a_stamp(client, staff, course):
    log_in(client, staff)
    start_thread(client, course)
    page = client.get("/board/threads/1").get_data(as_text=True)
    assert '<span class="stamp">Staff</span>' in page


# --- Starting threads -----------------------------------------------------------

def test_enrolled_student_can_start_a_thread(client, student, course):
    log_in(client, student)
    response = start_thread(client, course)

    thread = db.session.scalar(db.select(Thread))
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/board/threads/{thread.id}")
    assert thread.author == student and thread.course == course


def test_staff_can_post_without_joining(client, staff, course):
    log_in(client, staff)
    assert start_thread(client, course).status_code == 302


def test_outsider_cannot_start_a_thread(client, outsider, course):
    log_in(client, outsider)
    assert client.get(f"/board/{course.id}/new").status_code == 403
    assert start_thread(client, course).status_code == 403
    assert db.session.scalar(db.select(Thread)) is None


@pytest.mark.parametrize("overrides", [
    {"title": ""},
    {"title": "   "},
    {"body": ""},
    {"title": "x" * 201},
    {"body": "x" * 5001},
])
def test_invalid_thread_is_rejected(client, student, course, overrides):
    log_in(client, student)
    response = start_thread(client, course, **overrides)
    assert response.status_code == 200  # form shown again
    assert db.session.scalar(db.select(Thread)) is None


# --- Replying ---------------------------------------------------------------------

def test_reply_redirects_to_the_new_post(client, student, thread):
    log_in(client, student)
    response = post_reply(client, thread)

    post = db.session.scalar(db.select(Post))
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/board/threads/{thread.id}#post-{post.id}")
    assert post.body == "Check your loop condition."


def test_outsider_cannot_reply(client, outsider, thread):
    log_in(client, outsider)
    assert post_reply(client, thread).status_code == 403
    assert db.session.scalar(db.select(Post)) is None


def test_empty_reply_shows_errors(client, student, thread):
    log_in(client, student)
    response = post_reply(client, thread, body="   ")
    assert response.status_code == 400
    assert "This field is required." in response.get_data(as_text=True)
    assert db.session.scalar(db.select(Post)) is None


def test_reply_keeps_line_breaks_in_markup(client, student, thread):
    log_in(client, student)
    post_reply(client, thread, body="line one\nline two")
    page = client.get(f"/board/threads/{thread.id}").get_data(as_text=True)
    assert "line one\nline two" in page  # shown with white-space: pre-line


# --- Attachments ------------------------------------------------------------------

def test_attachment_is_saved_as_a_board_resource(app, client, student, thread):
    log_in(client, student)
    post_reply(client, thread, file=("lab2 fix.pdf", PDF_BYTES))

    post = db.session.scalar(db.select(Post))
    resource = post.attachment
    assert resource.title == "lab2_fix"  # secure_filename, without the extension
    assert resource.kind == "file" and resource.type == "other"
    assert resource.tag_list == ["board"]
    assert resource.course == thread.course and resource.uploader == student
    assert not resource.is_official
    assert uploaded_files(app) == [resource.file_path]


def test_staff_attachment_is_official(client, staff, thread):
    log_in(client, staff)
    post_reply(client, thread, file=("answers.pdf", PDF_BYTES))
    assert db.session.scalar(db.select(Resource)).is_official


def test_attachment_shows_in_thread_and_library(client, student, thread):
    log_in(client, student)
    post_reply(client, thread, file=("lab2.pdf", PDF_BYTES))
    resource = db.session.scalar(db.select(Resource))
    download = f"/courses/{thread.course_id}/resources/{resource.id}/download"

    assert download in client.get(f"/board/threads/{thread.id}").get_data(as_text=True)
    library = client.get(f"/courses/{thread.course_id}?q=board").get_data(as_text=True)
    assert "lab2" in library
    assert client.get(download).data == PDF_BYTES


def test_disallowed_attachment_is_rejected(app, client, student, thread):
    log_in(client, student)
    response = post_reply(client, thread, file=("virus.exe", b"MZ..."))
    assert response.status_code == 400
    assert "Allowed types" in response.get_data(as_text=True)
    assert db.session.scalar(db.select(Post)) is None
    assert uploaded_files(app) == []


def test_oversized_attachment_gets_413(client, student, thread):
    log_in(client, student)
    big = b"0" * (10 * 1024 * 1024 + 1)
    assert post_reply(client, thread, file=("big.pdf", big)).status_code == 413


# --- Deleting ---------------------------------------------------------------------

def test_author_can_delete_their_reply_and_its_file(app, client, student, thread):
    log_in(client, student)
    post_reply(client, thread, file=("lab2.pdf", PDF_BYTES))
    post = db.session.scalar(db.select(Post))

    response = client.post(f"/board/posts/{post.id}/delete")
    assert response.status_code == 302
    assert db.session.scalar(db.select(Post)) is None
    assert db.session.scalar(db.select(Resource)) is None
    assert uploaded_files(app) == []


def test_other_student_cannot_delete_reply(client, student, other_student, thread):
    db.session.add(Post(body="mine", thread=thread, author=student))
    db.session.commit()
    log_in(client, other_student)

    assert client.post("/board/posts/1/delete").status_code == 403
    assert client.post(f"/board/threads/{thread.id}/delete").status_code == 403
    assert db.session.get(Post, 1) is not None


def test_delete_buttons_only_shown_to_allowed_users(client, student, other_student, thread):
    log_in(client, other_student)
    page = client.get(f"/board/threads/{thread.id}").get_data(as_text=True)
    assert "/delete" not in page


def test_staff_can_delete_any_thread_with_replies_and_files(app, client, student, staff, thread):
    log_in(client, student)
    post_reply(client, thread, file=("lab2.pdf", PDF_BYTES))
    post_reply(client, thread, body="second reply")
    client.post("/auth/logout")

    log_in(client, staff)
    response = client.post(f"/board/threads/{thread.id}/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/board/{thread.course_id}/")
    assert db.session.scalar(db.select(Thread)) is None
    assert db.session.scalar(db.select(Post)) is None
    assert db.session.scalar(db.select(Resource)) is None
    assert uploaded_files(app) == []


def test_deleting_a_post_keeps_a_linked_library_resource(client, student, thread):
    """Only files attached on the board are removed; a library resource stays."""
    library = Resource(title="Week 1 notes", kind="link", url="https://example.com",
                       type="notes", course=thread.course, uploader=student)
    db.session.add(Post(body="see the notes", thread=thread, author=student, attachment=library))
    db.session.commit()
    log_in(client, student)

    client.post("/board/posts/1/delete")
    assert db.session.get(Resource, library.id) is not None


def test_deleting_an_attached_resource_from_the_library_keeps_the_post(client, student, thread):
    log_in(client, student)
    post_reply(client, thread, file=("lab2.pdf", PDF_BYTES))
    resource = db.session.scalar(db.select(Resource))

    client.post(f"/courses/{thread.course_id}/resources/{resource.id}/delete")
    post = db.session.scalar(db.select(Post))
    assert post is not None and post.attachment is None
    assert client.get(f"/board/threads/{thread.id}").status_code == 200


def test_deletes_need_post(client, student, thread):
    log_in(client, student)
    assert client.get(f"/board/threads/{thread.id}/delete").status_code == 405


# --- timeago filter ---------------------------------------------------------------

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("delta, expected", [
    (timedelta(seconds=5), "just now"),
    (timedelta(seconds=59), "just now"),
    (timedelta(minutes=1), "1 minute ago"),
    (timedelta(minutes=45), "45 minutes ago"),
    (timedelta(hours=1), "1 hour ago"),
    (timedelta(days=2), "2 days ago"),
    (timedelta(days=14), "2 weeks ago"),
    (timedelta(days=60), "2 months ago"),
    (timedelta(days=800), "2 years ago"),
])
def test_timeago(delta, expected):
    assert timeago(NOW - delta, now=NOW) == expected


def test_timeago_treats_naive_times_as_utc():
    naive = (NOW - timedelta(hours=3)).replace(tzinfo=None)
    assert timeago(naive, now=NOW) == "3 hours ago"


def test_timeago_of_none_is_blank():
    assert timeago(None) == ""

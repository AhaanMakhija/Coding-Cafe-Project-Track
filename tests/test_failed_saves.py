"""If saving to the database fails after a file was written, the file is deleted.

This cleanup never runs in normal use, so these tests force the commit to fail
(monkeypatch swaps db.session.commit for a function that raises).
"""

import io
import os

import pytest
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models import Course, Thread
from conftest import log_in

PDF_BYTES = b"%PDF-1.4 fake pdf for tests"


@pytest.fixture
def setup(app, make_user):
    """An enrolled student and a thread in their course."""
    course = Course(code="CS101", name="Intro to Programming", term="Fall 2026")
    student = make_user()
    student.courses.append(course)
    thread = Thread(title="Question", body="Help?", course=course, author=student)
    db.session.add(thread)
    db.session.commit()
    return course, student, thread


def break_commit(monkeypatch):
    def failing_commit():
        raise OperationalError("COMMIT", {}, Exception("database is locked"))
    monkeypatch.setattr(db.session, "commit", failing_commit)


def uploaded_files(app):
    folder = app.config["UPLOAD_FOLDER"]
    return os.listdir(folder) if os.path.isdir(folder) else []


def test_failed_resource_save_deletes_the_uploaded_file(app, client, setup, monkeypatch):
    course, student, _ = setup
    log_in(client, student)
    break_commit(monkeypatch)

    with pytest.raises(OperationalError):
        client.post(f"/courses/{course.id}/resources/new", content_type="multipart/form-data", data={
            "title": "Notes", "kind": "file", "resource_type": "notes", "tags": "",
            "file": (io.BytesIO(PDF_BYTES), "notes.pdf"),
        })
    assert uploaded_files(app) == []


def test_failed_reply_save_deletes_the_attachment(app, client, setup, monkeypatch):
    _, student, thread = setup
    log_in(client, student)
    break_commit(monkeypatch)

    with pytest.raises(OperationalError):
        client.post(f"/board/threads/{thread.id}/reply", content_type="multipart/form-data", data={
            "body": "Here you go", "file": (io.BytesIO(PDF_BYTES), "answer.pdf"),
        })
    assert uploaded_files(app) == []


def test_failed_save_shows_the_500_page(app, client, setup, monkeypatch):
    """With PROPAGATE_EXCEPTIONS off (as when running for real), users see the friendly page."""
    app.config["PROPAGATE_EXCEPTIONS"] = False
    course, student, _ = setup
    log_in(client, student)
    break_commit(monkeypatch)

    response = client.post(f"/courses/{course.id}/resources/new", data={
        "title": "Folder", "kind": "link", "resource_type": "notes", "tags": "",
        "url": "https://drive.google.com/drive/folders/abc",
    })
    assert response.status_code == 500
    assert "Something went wrong on our side." in response.get_data(as_text=True)

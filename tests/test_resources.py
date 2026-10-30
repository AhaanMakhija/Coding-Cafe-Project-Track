"""Tests for adding, listing and downloading resources, and the storage helper."""

import io
import os

import pytest
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import Course, Resource
from app.resources.storage import is_allowed_file, save_upload
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
def staff(make_user):
    return make_user(email="staff@plaksha.edu.in", role="staff", name="Prof Staff")


def upload(client, course, filename="Week 1 notes.pdf", content=PDF_BYTES, **overrides):
    data = {"title": "Week 1 notes", "kind": "file", "resource_type": "notes",
            "tags": "Week 1, intro", "file": (io.BytesIO(content), filename)}
    data.update(overrides)
    return client.post(f"/courses/{course.id}/resources/new", data=data,
                       content_type="multipart/form-data")


def add_link(client, course, url="https://drive.google.com/drive/folders/abc", **overrides):
    data = {"title": "Lecture folder", "kind": "link", "resource_type": "slides",
            "tags": "", "url": url}
    data.update(overrides)
    return client.post(f"/courses/{course.id}/resources/new", data=data)


def uploaded_files(app):
    folder = app.config["UPLOAD_FOLDER"]
    return os.listdir(folder) if os.path.isdir(folder) else []


# --- Storage helper -----------------------------------------------------------

@pytest.mark.parametrize("filename, allowed", [
    ("notes.pdf", True), ("SLIDES.PPTX", True), ("photo.jpeg", True),
    ("page.html", False), ("image.svg", False), ("virus.exe", False),
    ("script.py", False), ("notes", False), ("", False),
    ("notes.pdf.exe", False),  # only the last extension counts
])
def test_is_allowed_file(filename, allowed):
    assert is_allowed_file(filename) is allowed


def test_save_upload_uses_random_name(tmp_path):
    first = save_upload(FileStorage(io.BytesIO(PDF_BYTES), "notes.pdf"), str(tmp_path))
    second = save_upload(FileStorage(io.BytesIO(PDF_BYTES), "notes.pdf"), str(tmp_path))
    assert first != second  # same name uploaded twice does not overwrite
    assert first.endswith(".pdf") and "notes" not in first
    assert (tmp_path / first).read_bytes() == PDF_BYTES


def test_save_upload_ignores_path_in_filename(tmp_path):
    name = save_upload(FileStorage(io.BytesIO(PDF_BYTES), "../../evil.pdf"), str(tmp_path / "up"))
    assert os.path.dirname(name) == ""
    assert os.listdir(tmp_path / "up") == [name]


def test_save_upload_rejects_bad_type(tmp_path):
    with pytest.raises(ValueError):
        save_upload(FileStorage(io.BytesIO(b"<script>"), "page.html"), str(tmp_path))


# --- Uploading files ------------------------------------------------------------

def test_student_uploads_pdf(app, client, student, course):
    log_in(client, student)
    response = upload(client, course)
    assert response.status_code == 302

    resource = db.session.scalar(db.select(Resource))
    assert resource.kind == "file"
    assert resource.is_official is False
    assert resource.tags == "week 1, intro"
    assert uploaded_files(app) == [resource.file_path]

    page = client.get(f"/courses/{course.id}").data
    assert b"Week 1 notes" in page
    assert b"Unofficial" in page


def test_staff_upload_is_official(client, staff, course):
    log_in(client, staff)  # staff need not be enrolled
    assert upload(client, course).status_code == 302
    assert db.session.scalar(db.select(Resource)).is_official is True


def test_student_must_join_before_adding(make_user, client, course):
    outsider = make_user(email="outsider@plaksha.edu.in")
    log_in(client, outsider)
    assert client.get(f"/courses/{course.id}/resources/new").status_code == 403
    assert upload(client, course).status_code == 403
    assert db.session.query(Resource).count() == 0


def test_disallowed_file_type_is_rejected(app, client, student, course):
    log_in(client, student)
    response = upload(client, course, filename="page.html", content=b"<script>alert(1)</script>")
    assert response.status_code == 200
    assert b"Allowed types" in response.data
    assert db.session.query(Resource).count() == 0
    assert uploaded_files(app) == []


def test_file_kind_without_file_is_rejected(client, student, course):
    log_in(client, student)
    response = upload(client, course, file=(io.BytesIO(b""), ""))
    assert b"Choose a file to upload." in response.data
    assert db.session.query(Resource).count() == 0


def test_file_over_10_mb_is_rejected(app, client, student, course):
    log_in(client, student)
    big = b"0" * (10 * 1024 * 1024 + 1)
    response = upload(client, course, content=big)
    assert response.status_code == 413
    assert b"too large" in response.data
    assert uploaded_files(app) == []


# --- Saving links -----------------------------------------------------------------

def test_student_saves_link(client, student, course):
    log_in(client, student)
    assert add_link(client, course).status_code == 302

    resource = db.session.scalar(db.select(Resource))
    assert resource.kind == "link"
    assert resource.file_path is None
    assert b"https://drive.google.com/drive/folders/abc" in client.get(f"/courses/{course.id}").data


@pytest.mark.parametrize("url", [
    "",                           # missing
    "javascript:alert(1)",        # would run code when clicked
    "drive.google.com/folder",    # no scheme
    "ftp://files.example.com/x",  # not a web link
])
def test_bad_links_are_rejected(client, student, course, url):
    log_in(client, student)
    response = add_link(client, course, url=url)
    assert response.status_code == 200
    assert db.session.query(Resource).count() == 0


# --- Downloading -----------------------------------------------------------------

def test_download_returns_file_as_attachment(client, student, course):
    log_in(client, student)
    upload(client, course)
    resource = db.session.scalar(db.select(Resource))

    response = client.get(f"/courses/{course.id}/resources/{resource.id}/download")
    assert response.status_code == 200
    assert response.data == PDF_BYTES
    disposition = response.headers["Content-Disposition"]
    assert disposition.startswith("attachment")
    assert "Week_1_notes.pdf" in disposition


def test_download_requires_login(client, student, course):
    log_in(client, student)
    upload(client, course)
    resource = db.session.scalar(db.select(Resource))
    client.post("/auth/logout")
    response = client.get(f"/courses/{course.id}/resources/{resource.id}/download")
    assert response.status_code == 302


def test_download_with_wrong_course_is_404(client, student, course):
    log_in(client, student)
    upload(client, course)
    resource = db.session.scalar(db.select(Resource))
    assert client.get(f"/courses/999/resources/{resource.id}/download").status_code == 404


def test_download_of_link_is_404(client, student, course):
    log_in(client, student)
    add_link(client, course)
    resource = db.session.scalar(db.select(Resource))
    assert client.get(f"/courses/{course.id}/resources/{resource.id}/download").status_code == 404

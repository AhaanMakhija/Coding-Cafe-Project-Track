"""Tests for the 'use a link instead' features: link labels, form hint and 413 page."""

import io
import re

import pytest

from app.extensions import db
from app.models import Course
from app.resources.links import link_source
from conftest import log_in


@pytest.fixture
def course(app):
    course = Course(code="CS101", name="Intro to Programming", term="Fall 2026")
    db.session.add(course)
    db.session.commit()
    return course


@pytest.fixture
def student(make_user, course):
    user = make_user()
    user.courses.append(course)
    db.session.commit()
    return user


# --- link_source ------------------------------------------------------------------

@pytest.mark.parametrize("url, expected", [
    ("https://drive.google.com/drive/folders/abc", "Google Drive"),
    ("https://docs.google.com/document/d/xyz", "Google Docs"),
    ("https://1drv.ms/b/s!abc", "OneDrive"),
    ("https://plaksha-my.sharepoint.com/:b:/g/file", "OneDrive"),  # subdomain match
    ("https://www.youtube.com/watch?v=abc", "YouTube"),
    ("https://youtu.be/abc", "YouTube"),
    ("https://WWW.Example.com/page", "example.com"),               # unknown site: show host
    ("https://notyoutube.com/watch", "notyoutube.com"),           # look-alike is not YouTube
    ("", ""),
    (None, ""),
])
def test_link_source(url, expected):
    assert link_source(url) == expected


def test_course_page_shows_link_source(client, student, course):
    log_in(client, student)
    client.post(f"/courses/{course.id}/resources/new", data={
        "title": "Lecture recording", "kind": "link", "resource_type": "other",
        "tags": "", "url": "https://www.youtube.com/watch?v=abc",
    })
    assert b"Link \xc2\xb7 YouTube" in client.get(f"/courses/{course.id}").data  # \xc2\xb7 is "·"


# --- Form hint and ?kind=link -------------------------------------------------------

def checked_kind(page):
    """Which "kind" radio button is checked in the page's HTML, in any attribute order."""
    for tag in re.findall(rb'<input[^>]*name="kind"[^>]*>', page):
        if b" checked" in tag:
            return re.search(rb'value="(\w+)"', tag).group(1).decode()
    return None


def test_form_suggests_link_for_big_files(client, student, course):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}/resources/new").data
    assert b"Bigger than 10 MB?" in page


def test_form_defaults_to_file(client, student, course):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}/resources/new").data
    assert checked_kind(page) == "file"


def test_kind_link_in_url_preselects_link(client, student, course):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}/resources/new?kind=link").data
    assert checked_kind(page) == "link"


def test_unknown_kind_in_url_is_ignored(client, student, course):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}/resources/new?kind=video").data
    assert checked_kind(page) == "file"


# --- 413 page -------------------------------------------------------------------------

def test_too_large_page_offers_link_form(client, student, course):
    log_in(client, student)
    big = io.BytesIO(b"0" * (10 * 1024 * 1024 + 1))
    response = client.post(f"/courses/{course.id}/resources/new", data={
        "title": "Huge video", "kind": "file", "resource_type": "other",
        "file": (big, "lecture.pdf"),
    }, content_type="multipart/form-data")

    assert response.status_code == 413
    assert b"Add as a link instead" in response.data
    assert f"/courses/{course.id}/resources/new?kind=link".encode() in response.data

"""Week 4 tests: searching and filtering the library, and editing/deleting resources."""

import io
import os
from datetime import datetime

import pytest
from werkzeug.datastructures import MultiDict

from app.extensions import db
from app.models import Course, Post, Resource, Thread
from app.resources.queries import ResourceFilters, filter_resources
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


@pytest.fixture
def other_student(make_user, course):
    user = make_user(email="other@plaksha.edu.in", name="Olly Other")
    user.courses.append(course)
    db.session.commit()
    return user


@pytest.fixture
def staff(make_user):
    return make_user(email="staff@plaksha.edu.in", role="staff", name="Prof Staff")


def add_resource(course, uploader, title, *, type="notes", tags="", official=False,
                 kind="link", day=1):
    resource = Resource(
        title=title, kind=kind, type=type, tags=tags, is_official=official,
        course=course, uploader=uploader, created_at=datetime(2026, 10, day),
        url="https://example.com/" + title.replace(" ", "-") if kind == "link" else None,
        file_path=None if kind == "link" else "stored.pdf",
    )
    db.session.add(resource)
    db.session.commit()
    return resource


@pytest.fixture
def library(course, student, staff):
    """Four resources with different titles, types, tags and sources."""
    return [
        add_resource(course, staff, "Midterm past paper", type="past paper", tags="midterm, 2025",
                     official=True, day=1),
        add_resource(course, student, "My midterm notes", tags="midterm", day=2),
        add_resource(course, student, "Loops cheat sheet", tags="week 3, loops", day=3),
        add_resource(course, staff, "Lecture 5 slides", type="slides", official=True, day=4),
    ]


def titles(resources):
    return [r.title for r in resources]


# --- ResourceFilters.from_args ------------------------------------------------------------

def test_filters_read_from_url():
    f = ResourceFilters.from_args(MultiDict({"q": "  midterm ", "type": "slides", "official": "official"}))
    assert (f.q, f.type, f.official, f.active) == ("midterm", "slides", "official", True)


def test_unknown_filter_values_are_ignored():
    f = ResourceFilters.from_args(MultiDict({"type": "meme", "official": "maybe"}))
    assert (f.type, f.official, f.active) == ("", "", False)


def test_search_text_is_capped():
    assert len(ResourceFilters.from_args(MultiDict({"q": "x" * 500})).q) == 100


# --- filter_resources ------------------------------------------------------------------

def test_no_filters_returns_all_newest_first(course, library):
    assert titles(filter_resources(course, ResourceFilters())) == [
        "Lecture 5 slides", "Loops cheat sheet", "My midterm notes", "Midterm past paper",
    ]


def test_search_matches_title_case_insensitively(course, library):
    assert titles(filter_resources(course, ResourceFilters(q="LOOPS"))) == ["Loops cheat sheet"]


def test_search_matches_tags(course, library):
    assert titles(filter_resources(course, ResourceFilters(q="week 3"))) == ["Loops cheat sheet"]


def test_search_matches_title_or_tag(course, library):
    assert titles(filter_resources(course, ResourceFilters(q="midterm"))) == [
        "My midterm notes", "Midterm past paper",
    ]


def test_search_wildcards_are_literal(course, library):
    # Without autoescape, "%" would match everything.
    assert filter_resources(course, ResourceFilters(q="%")) == []
    assert filter_resources(course, ResourceFilters(q="_")) == []


def test_filter_by_type(course, library):
    assert titles(filter_resources(course, ResourceFilters(type="slides"))) == ["Lecture 5 slides"]


@pytest.mark.parametrize("official, expected", [
    ("official", ["Lecture 5 slides", "Midterm past paper"]),
    ("unofficial", ["Loops cheat sheet", "My midterm notes"]),
])
def test_filter_by_source(course, library, official, expected):
    assert titles(filter_resources(course, ResourceFilters(official=official))) == expected


def test_filters_combine(course, library):
    f = ResourceFilters(q="midterm", official="official")
    assert titles(filter_resources(course, f)) == ["Midterm past paper"]


def test_other_courses_are_not_searched(app, course, library, staff):
    other = Course(code="MA102", name="Calculus", term="Fall 2026")
    db.session.add(other)
    db.session.commit()
    add_resource(other, staff, "Midterm calculus", day=5)
    assert "Midterm calculus" not in titles(filter_resources(course, ResourceFilters(q="midterm")))


# --- The course page with filters ---------------------------------------------------------

def test_course_page_filters_from_url(client, student, course, library):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}?q=loops").data
    assert b"Loops cheat sheet" in page
    assert b"Lecture 5 slides" not in page
    assert b"Showing 1 of 4 resources." in page


def test_course_page_no_matches(client, student, course, library):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}?q=nothing-like-this").data
    assert b"Nothing matches those filters." in page


def test_tags_link_to_a_search(client, student, course, library):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}").data
    assert f'href="/courses/{course.id}?q=loops"'.encode() in page


def test_bad_filter_values_do_not_error(client, student, course, library):
    log_in(client, student)
    assert client.get(f"/courses/{course.id}?type=meme&official=maybe").status_code == 200


# --- Editing ------------------------------------------------------------------------

def edit(client, resource, **fields):
    data = {"title": resource.title, "url": resource.url or "", "resource_type": resource.type,
            "tags": resource.tags}
    data.update(fields)
    return client.post(f"/courses/{resource.course_id}/resources/{resource.id}/edit", data=data)


def test_uploader_can_edit(client, student, course, library):
    mine = library[2]
    log_in(client, student)
    assert client.get(f"/courses/{course.id}/resources/{mine.id}/edit").status_code == 200

    response = edit(client, mine, title="Loops and lists", tags="Week 3, LISTS", resource_type="other")
    assert response.status_code == 302
    assert (mine.title, mine.tags, mine.type) == ("Loops and lists", "week 3, lists", "other")


def test_edit_form_is_prefilled(client, student, course, library):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}/resources/{library[2].id}/edit").data
    assert b'value="Loops cheat sheet"' in page


def test_other_student_cannot_edit(client, other_student, course, library):
    log_in(client, other_student)
    assert client.get(f"/courses/{course.id}/resources/{library[2].id}/edit").status_code == 403
    assert edit(client, library[2], title="Hacked").status_code == 403
    assert library[2].title == "Loops cheat sheet"


def test_staff_cannot_edit_others_work(client, staff, course, library):
    log_in(client, staff)
    assert edit(client, library[2], title="Changed by staff").status_code == 403


def test_edit_link_rejects_javascript_url(client, student, course, library):
    log_in(client, student)
    response = edit(client, library[2], url="javascript:alert(1)")
    assert response.status_code == 200
    assert library[2].url.startswith("https://")


def test_edit_requires_title(client, student, course, library):
    log_in(client, student)
    response = edit(client, library[2], title="   ")
    assert b"This field is required" in response.data


def test_edit_with_wrong_course_is_404(client, student, library):
    log_in(client, student)
    assert client.get(f"/courses/999/resources/{library[2].id}/edit").status_code == 404


def test_page_shows_edit_only_on_own_resources(client, student, course, library):
    log_in(client, student)
    page = client.get(f"/courses/{course.id}").data.decode()
    assert f"/resources/{library[2].id}/edit" in page      # mine
    assert f"/resources/{library[0].id}/edit" not in page  # staff's


# --- Deleting --------------------------------------------------------------------

def delete(client, resource):
    return client.post(f"/courses/{resource.course_id}/resources/{resource.id}/delete")


def test_uploader_deletes_file_and_it_leaves_disk(app, client, student, course):
    log_in(client, student)
    client.post(f"/courses/{course.id}/resources/new", data={
        "title": "Old notes", "kind": "file", "resource_type": "notes", "tags": "",
        "file": (io.BytesIO(b"%PDF-1.4 test"), "old.pdf"),
    }, content_type="multipart/form-data")
    resource = db.session.scalar(db.select(Resource))
    stored = os.path.join(app.config["UPLOAD_FOLDER"], resource.file_path)
    assert os.path.isfile(stored)

    assert delete(client, resource).status_code == 302
    assert db.session.query(Resource).count() == 0
    assert not os.path.exists(stored)


def test_staff_can_delete_student_resource(client, staff, course, library):
    log_in(client, staff)
    assert delete(client, library[2]).status_code == 302
    assert db.session.get(Resource, library[2].id) is None


def test_other_student_cannot_delete(client, other_student, course, library):
    log_in(client, other_student)
    assert delete(client, library[2]).status_code == 403
    assert db.session.get(Resource, library[2].id) is not None


def test_delete_rejects_get(client, student, course, library):
    log_in(client, student)
    assert client.get(f"/courses/{course.id}/resources/{library[2].id}/delete").status_code == 405


def test_delete_keeps_forum_post_but_drops_attachment(client, student, course, library):
    thread = Thread(title="Help", body="Question", course=course, author=student)
    post = Post(body="See my notes", author=student, thread=thread, attachment=library[2])
    db.session.add(post)
    db.session.commit()

    log_in(client, student)
    delete(client, library[2])
    db.session.refresh(post)
    assert post.attachment_resource_id is None
    assert post.body == "See my notes"


# --- Titles are shown safely ----------------------------------------------------------

def test_title_with_quotes_and_html_is_escaped(client, student, course):
    add_resource(course, student, "Notes'); alert(1); ('<b>")
    log_in(client, student)
    page = client.get(f"/courses/{course.id}").data
    assert b"&lt;b&gt;" in page               # shown as text, not as HTML
    assert b"('<b>" not in page                # the raw title never appears
    assert b"confirm('Delete this resource?" in page  # the JS confirm has fixed text only

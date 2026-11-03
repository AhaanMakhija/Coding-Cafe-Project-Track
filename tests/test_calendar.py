"""Week 5 tests: campus events, weekly classes and the FullCalendar JSON feeds."""

from datetime import datetime, time

import pytest

from app.calendar.feeds import parse_fc_datetime, to_fc_weekday
from app.extensions import db
from app.models import ClassSlot, Course, Event
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
def staff(make_user):
    return make_user(email="staff@plaksha.edu.in", role="staff", name="Prof Staff")


def make_event(creator, title="Hackathon", start=datetime(2026, 11, 7, 10), end=datetime(2026, 11, 7, 18)):
    event = Event(title=title, start_at=start, end_at=end, location="Main hall", creator=creator)
    db.session.add(event)
    db.session.commit()
    return event


def make_slot(user, course, weekday=0, start=time(10), end=time(11, 30), room="204"):
    slot = ClassSlot(user=user, course=course, weekday=weekday, start_time=start, end_time=end, room=room)
    db.session.add(slot)
    db.session.commit()
    return slot


EVENT_FORM = {"title": "Career fair", "start_at": "2026-11-12T14:00", "end_at": "2026-11-12T17:30",
              "location": "Atrium", "description": "Bring your CV.\nAll years welcome."}


# --- Small helpers -------------------------------------------------------------------

@pytest.mark.parametrize("ours, fullcalendar", [(0, 1), (1, 2), (4, 5), (5, 6), (6, 0)])
def test_weekday_conversion(ours, fullcalendar):
    """Python counts Monday as 0; FullCalendar counts Sunday as 0."""
    assert to_fc_weekday(ours) == fullcalendar


def test_parse_fc_datetime_drops_timezone():
    assert parse_fc_datetime("2026-10-26T00:00:00+05:30") == datetime(2026, 10, 26)
    assert parse_fc_datetime("") is None
    with pytest.raises(ValueError):
        parse_fc_datetime("next tuesday")


# --- Pages need login ------------------------------------------------------------------

@pytest.mark.parametrize("url", ["/calendar/", "/calendar/api/events", "/calendar/api/classes",
                                 "/calendar/classes/new"])
def test_calendar_requires_login(client, url):
    assert client.get(url).status_code == 302


def test_calendar_page_loads(client, student):
    log_in(client, student)
    page = client.get("/calendar/").data
    assert b'id="calendar"' in page
    assert b"/calendar/api/events" in page
    assert b"New campus event" not in page  # students don't see staff tools


# --- Campus events ------------------------------------------------------------------------

def test_staff_creates_event(client, staff):
    log_in(client, staff)
    response = client.post("/calendar/events/new", data=EVENT_FORM)
    assert response.status_code == 302

    event = db.session.scalar(db.select(Event))
    assert event.start_at == datetime(2026, 11, 12, 14, 0)
    assert event.creator == staff
    page = client.get(f"/calendar/events/{event.id}").data
    assert b"Career fair" in page and b"Atrium" in page


def test_student_cannot_manage_events(client, student, staff):
    event = make_event(staff)
    log_in(client, student)
    assert client.post("/calendar/events/new", data=EVENT_FORM).status_code == 403
    assert client.post(f"/calendar/events/{event.id}/edit", data=EVENT_FORM).status_code == 403
    assert client.post(f"/calendar/events/{event.id}/delete").status_code == 403
    assert client.get(f"/calendar/events/{event.id}").status_code == 200  # can still view


@pytest.mark.parametrize("end", ["2026-11-12T13:00", "2026-11-12T14:00"])
def test_event_must_end_after_start(client, staff, end):
    log_in(client, staff)
    response = client.post("/calendar/events/new", data={**EVENT_FORM, "end_at": end})
    assert b"must end after it starts" in response.data
    assert db.session.query(Event).count() == 0


def test_event_rejects_bad_date(client, staff):
    log_in(client, staff)
    response = client.post("/calendar/events/new", data={**EVENT_FORM, "start_at": "soon"})
    assert response.status_code == 200
    assert db.session.query(Event).count() == 0


def test_staff_edits_and_deletes_event(client, staff):
    event = make_event(staff)
    log_in(client, staff)
    assert b'value="Hackathon"' in client.get(f"/calendar/events/{event.id}/edit").data  # prefilled

    client.post(f"/calendar/events/{event.id}/edit", data={**EVENT_FORM, "title": "Hackathon 2.0"})
    assert event.title == "Hackathon 2.0"

    client.post(f"/calendar/events/{event.id}/delete")
    assert db.session.get(Event, event.id) is None


def test_event_description_html_is_escaped(client, staff):
    log_in(client, staff)
    client.post("/calendar/events/new", data={**EVENT_FORM, "description": "<script>alert(1)</script>"})
    event = db.session.scalar(db.select(Event))
    assert b"<script>alert(1)" not in client.get(f"/calendar/events/{event.id}").data


# --- Events feed --------------------------------------------------------------------------

def test_events_feed_format(client, student, staff):
    event = make_event(staff)
    log_in(client, student)
    data = client.get("/calendar/api/events").get_json()
    assert data == [{
        "id": f"event-{event.id}", "title": "Hackathon",
        "start": "2026-11-07T10:00", "end": "2026-11-07T18:00",
        "url": f"/calendar/events/{event.id}",
        "extendedProps": {"layer": "campus", "location": "Main hall"},
    }]


def test_events_feed_only_returns_visible_range(client, student, staff):
    make_event(staff, "Before", datetime(2026, 10, 1, 9), datetime(2026, 10, 1, 10))
    make_event(staff, "Inside", datetime(2026, 11, 3, 9), datetime(2026, 11, 3, 10))
    make_event(staff, "Overlaps start", datetime(2026, 11, 1, 23), datetime(2026, 11, 2, 1))
    make_event(staff, "After", datetime(2026, 12, 1, 9), datetime(2026, 12, 1, 10))
    log_in(client, student)

    data = client.get("/calendar/api/events?start=2026-11-02T00:00:00%2B05:30"
                      "&end=2026-11-09T00:00:00%2B05:30").get_json()
    assert [e["title"] for e in data] == ["Overlaps start", "Inside"]


def test_events_feed_rejects_bad_range(client, student):
    log_in(client, student)
    assert client.get("/calendar/api/events?start=yesterday").status_code == 400


# --- Weekly classes ---------------------------------------------------------------------

def class_form(course, **overrides):
    data = {"course_id": course.id, "weekday": 2, "start_time": "09:00", "end_time": "10:30", "room": "204"}
    data.update(overrides)
    return data


def test_student_adds_class(client, student, course):
    log_in(client, student)
    response = client.post("/calendar/classes/new", data=class_form(course))
    assert response.status_code == 302

    slot = db.session.scalar(db.select(ClassSlot))
    assert (slot.weekday, slot.start_time, slot.end_time) == (2, time(9), time(10, 30))
    assert slot.weekday_name == "Wednesday"
    assert slot.user == student


def test_class_must_end_after_start(client, student, course):
    log_in(client, student)
    response = client.post("/calendar/classes/new", data=class_form(course, end_time="08:00"))
    assert b"must end after it starts" in response.data
    assert db.session.query(ClassSlot).count() == 0


def test_class_only_for_joined_courses(app, client, student):
    other = Course(code="MA102", name="Calculus", term="Fall 2026")
    db.session.add(other)
    db.session.commit()
    log_in(client, student)
    response = client.post("/calendar/classes/new", data=class_form(other))
    assert b"Not a valid choice" in response.data
    assert db.session.query(ClassSlot).count() == 0


def test_add_class_without_courses_redirects(make_user, client):
    loner = make_user(email="loner@plaksha.edu.in")
    log_in(client, loner)
    response = client.get("/calendar/classes/new")
    assert response.status_code == 302
    assert response.headers["Location"] == "/courses/"


def test_classes_feed_is_weekly_and_personal(make_user, client, student, course):
    make_slot(student, course, weekday=0, room="204")       # Monday
    other = make_user(email="other@plaksha.edu.in")
    other.courses.append(course)
    make_slot(other, course, weekday=3)                      # someone else's
    log_in(client, student)

    data = client.get("/calendar/api/classes").get_json()
    assert len(data) == 1
    assert data[0]["title"] == "CS101 · 204"
    assert data[0]["daysOfWeek"] == [1]                      # Monday in FullCalendar
    assert (data[0]["startTime"], data[0]["endTime"]) == ("10:00", "11:30")
    assert data[0]["url"] == f"/courses/{course.id}"


def test_delete_own_class_only(make_user, client, student, course):
    mine = make_slot(student, course)
    other = make_user(email="other@plaksha.edu.in")
    other.courses.append(course)
    theirs = make_slot(other, course)
    log_in(client, student)

    assert client.post(f"/calendar/classes/{theirs.id}/delete").status_code == 403
    assert client.post(f"/calendar/classes/{mine.id}/delete").status_code == 302
    assert db.session.get(ClassSlot, mine.id) is None
    assert db.session.get(ClassSlot, theirs.id) is not None


def test_calendar_page_lists_my_classes(client, student, course):
    make_slot(student, course, weekday=4, start=time(14), end=time(15))
    log_in(client, student)
    page = client.get("/calendar/").data
    assert b"Fri" in page and b"14:00" in page

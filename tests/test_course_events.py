"""Tests for course calendars: course events, venue clashes, AM/PM times and .ics downloads."""

from datetime import date, datetime, time, timedelta

import pytest

from app.calendar.forms import TIME_CHOICES
from app.calendar.ics import escape, fold, next_weekday
from app.extensions import db
from app.models import ClassSlot, Course, Event
from app.template_filters import clock
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
def classmate(make_user, course):
    user = make_user(email="classmate@plaksha.edu.in", name="Cam Classmate")
    user.courses.append(course)
    db.session.commit()
    return user


@pytest.fixture
def staff(make_user):
    return make_user(email="staff@plaksha.edu.in", role="staff", name="Prof Staff")


def event_form(course, **overrides):
    data = {"title": "Midterm", "course_id": course.id, "day": "2026-12-03", "start_time": "10:00",
            "end_time": "12:00", "location": "Lecture hall 1", "description": ""}
    data.update(overrides)
    return data


def make_event(creator, course=None, title="Talk", day=date(2026, 12, 3), start=time(10), end=time(12),
               location="Lecture hall 1"):
    event = Event(title=title, course=course, creator=creator, location=location,
                  start_at=datetime.combine(day, start), end_at=datetime.combine(day, end))
    db.session.add(event)
    db.session.commit()
    return event


# --- AM/PM times --------------------------------------------------------------------

@pytest.mark.parametrize("moment, expected", [
    (time(0, 0), "12:00 AM"), (time(9, 5), "9:05 AM"), (time(12, 0), "12:00 PM"),
    (time(14, 30), "2:30 PM"), (time(23, 45), "11:45 PM"), (datetime(2026, 1, 1, 13, 15), "1:15 PM"),
])
def test_clock_filter(moment, expected):
    assert clock(moment) == expected


def test_time_dropdown_has_every_quarter_hour_with_am_pm():
    assert len(TIME_CHOICES) == 96
    labels = {c.value: c.label for c in TIME_CHOICES}
    assert labels["00:00"] == "12:00 AM" and labels["14:30"] == "2:30 PM"


def test_event_form_shows_am_pm_dropdowns(client, student):
    log_in(client, student)
    page = client.get("/calendar/events/new").get_data(as_text=True)
    assert '<select id="start_time"' in page
    assert '<option value="14:30">2:30 PM</option>' in page
    assert 'type="time"' not in page


def test_class_form_uses_am_pm_dropdowns_too(client, student):
    log_in(client, student)
    assert b'<option selected value="09:00">9:00 AM</option>' in client.get("/calendar/classes/new").data


def test_made_up_time_is_rejected(client, student, course):
    log_in(client, student)
    response = client.post("/calendar/events/new", data=event_form(course, start_time="10:07"))
    assert b"Not a valid choice" in response.data
    assert db.session.scalar(db.select(Event)) is None


# --- Adding course events ------------------------------------------------------------

def test_enrolled_student_adds_course_event(client, student, course):
    log_in(client, student)
    response = client.post("/calendar/events/new", data=event_form(course))
    assert response.status_code == 302

    event = db.session.scalar(db.select(Event))
    assert event.course == course and event.creator == student
    assert (event.start_at, event.end_at) == (datetime(2026, 12, 3, 10), datetime(2026, 12, 3, 12))
    page = client.get(f"/calendar/events/{event.id}").get_data(as_text=True)
    assert "10:00 AM – 12:00 PM" in page and "CS101" in page


def test_course_page_preselects_its_calendar(client, student, course):
    log_in(client, student)
    page = client.get(f"/calendar/events/new?course_id={course.id}").get_data(as_text=True)
    assert f'<option selected value="{course.id}">' in page


def test_student_cannot_add_to_a_course_they_have_not_joined(client, student):
    other = Course(code="MA102", name="Calculus", term="Fall 2026")
    db.session.add(other)
    db.session.commit()
    log_in(client, student)
    response = client.post("/calendar/events/new", data=event_form(other))
    assert b"Not a valid choice" in response.data
    assert db.session.scalar(db.select(Event)) is None


def test_student_without_courses_is_sent_to_join_one(client, make_user):
    log_in(client, make_user(email="new@plaksha.edu.in"))
    response = client.get("/calendar/events/new")
    assert response.status_code == 302 and response.headers["Location"] == "/courses/"


def test_staff_can_post_to_any_course_or_campus(client, staff, course):
    log_in(client, staff)
    page = client.get("/calendar/events/new").get_data(as_text=True)
    assert "Campus-wide (everyone)" in page and "CS101" in page
    assert client.post("/calendar/events/new", data=event_form(course)).status_code == 302


def test_creator_can_edit_but_classmate_cannot(client, student, classmate, course):
    event = make_event(student, course)
    log_in(client, classmate)
    assert client.post(f"/calendar/events/{event.id}/edit", data=event_form(course)).status_code == 403
    assert client.post(f"/calendar/events/{event.id}/delete").status_code == 403
    client.post("/auth/logout")

    log_in(client, student)
    client.post(f"/calendar/events/{event.id}/edit", data=event_form(course, title="Midterm (moved)"))
    assert event.title == "Midterm (moved)"


def test_staff_can_delete_a_student_event(client, student, staff, course):
    event = make_event(student, course)
    log_in(client, staff)
    response = client.post(f"/calendar/events/{event.id}/delete")
    assert response.headers["Location"] == f"/courses/{course.id}"  # back to the course
    assert db.session.get(Event, event.id) is None


# --- Who sees course events ------------------------------------------------------------

def test_course_events_feed_only_shows_my_courses(client, student, staff, course):
    other = Course(code="MA102", name="Calculus", term="Fall 2026")
    make_event(staff, course, title="Midterm")
    make_event(staff, other, title="Quiz", location="Room 112")
    make_event(staff, None, title="Career fair", location="Atrium")
    log_in(client, student)

    course_feed = client.get("/calendar/api/course-events").get_json()
    assert [e["title"] for e in course_feed] == ["CS101: Midterm"]
    assert course_feed[0]["extendedProps"]["layer"] == "course"
    assert [e["title"] for e in client.get("/calendar/api/events").get_json()] == ["Career fair"]


def test_course_page_lists_upcoming_events(client, student, staff, course):
    soon = date.today() + timedelta(days=2)
    make_event(staff, course, title="Lab 3 due", day=soon, start=time(14), end=time(15))
    make_event(staff, course, title="Old quiz", day=date.today() - timedelta(days=5))
    log_in(client, student)
    page = client.get(f"/courses/{course.id}").get_data(as_text=True)
    assert "Lab 3 due" in page and "2:00 PM–3:00 PM" in page
    assert "Old quiz" not in page
    assert f"/calendar/courses/{course.id}.ics" in page


# --- Venue clashes -------------------------------------------------------------------

def test_same_venue_same_time_is_blocked_across_accounts(client, student, staff, course):
    make_event(staff, None, title="Guest talk", start=time(10), end=time(12))
    log_in(client, student)
    response = client.post("/calendar/events/new",
                           data=event_form(course, start_time="11:00", end_time="13:00"))
    page = response.get_data(as_text=True)
    assert "Lecture hall 1 is already booked for “Guest talk”" in page
    assert "10:00 AM–12:00 PM" in page
    assert len(db.session.scalars(db.select(Event)).all()) == 1


@pytest.mark.parametrize("start, end, clashes", [
    ("09:00", "10:00", False),  # ends exactly when the other starts
    ("12:00", "13:00", False),  # starts exactly when the other ends
    ("09:00", "10:15", True),   # overlaps the start
    ("11:45", "13:00", True),   # overlaps the end
    ("10:30", "11:00", True),   # inside it
    ("08:00", "14:00", True),   # around it
])
def test_overlap_rule(client, student, staff, course, start, end, clashes):
    make_event(staff, None, start=time(10), end=time(12))
    log_in(client, student)
    response = client.post("/calendar/events/new", data=event_form(course, start_time=start, end_time=end))
    assert (b"already booked" in response.data) == clashes


def test_venue_names_match_ignoring_case_and_spaces(client, student, staff, course):
    make_event(staff, None, location="Lecture hall 1")
    log_in(client, student)
    response = client.post("/calendar/events/new", data=event_form(course, location="  lecture   HALL 1 "))
    assert b"already booked" in response.data


def test_other_venue_or_day_is_fine(client, student, staff, course):
    make_event(staff, None)
    log_in(client, student)
    assert client.post("/calendar/events/new", data=event_form(course, location="Room 204")).status_code == 302
    assert client.post("/calendar/events/new", data=event_form(course, title="Retake",
                                                               day="2026-12-04")).status_code == 302


def test_events_without_a_venue_never_clash(client, student, staff, course):
    make_event(staff, None, location="")
    log_in(client, student)
    assert client.post("/calendar/events/new", data=event_form(course, location="")).status_code == 302


def test_editing_an_event_does_not_clash_with_itself(client, student, course):
    event = make_event(student, course)
    log_in(client, student)
    response = client.post(f"/calendar/events/{event.id}/edit",
                           data=event_form(course, title="Midterm", end_time="12:30"))
    assert response.status_code == 302
    assert event.end_at == datetime(2026, 12, 3, 12, 30)


def test_moving_an_event_onto_a_booked_slot_is_blocked(client, student, staff, course):
    make_event(staff, None, title="Guest talk")
    mine = make_event(student, course, title="Study group", location="Room 204")
    log_in(client, student)
    response = client.post(f"/calendar/events/{mine.id}/edit", data=event_form(course, title="Study group"))
    assert b"already booked" in response.data
    assert mine.location == "Room 204"


def test_demo_data_has_no_venue_clashes(app):
    app.test_cli_runner().invoke(args=["seed-demo", "--password", "demo-pass-123"])
    events = db.session.scalars(db.select(Event).where(Event.location != "")).all()
    for a in events:
        for b in events:
            if a.id < b.id and a.location.lower() == b.location.lower():
                assert not (a.start_at < b.end_at and a.end_at > b.start_at), (a.title, b.title)


# --- .ics download -------------------------------------------------------------------

def test_ics_helpers():
    assert escape("Lab, part 1; bring notes\nand a pen") == "Lab\\, part 1\\; bring notes\\nand a pen"
    long = "DESCRIPTION:" + "x" * 200
    folded = fold(long)
    assert all(len(line.encode()) <= 75 for line in folded.split("\r\n"))
    assert folded.replace("\r\n ", "") == long
    assert next_weekday(0, date(2026, 11, 26)) == date(2026, 11, 30)  # Thursday -> next Monday
    assert next_weekday(3, date(2026, 11, 26)) == date(2026, 11, 26)  # same day counts


def test_fold_never_splits_a_multibyte_character():
    folded = fold("SUMMARY:" + "·" * 60)
    for line in folded.split("\r\n"):
        line.encode("utf-8").decode("utf-8")  # would raise if a character were cut
    assert folded.replace("\r\n ", "") == "SUMMARY:" + "·" * 60


def test_course_ics_download(client, student, staff, course):
    make_event(staff, course, title="Midterm, part 1", location="Lecture hall 1")
    db.session.add(ClassSlot(user=student, course=course, weekday=0, start_time=time(10),
                             end_time=time(11, 30), room="204"))
    db.session.commit()
    log_in(client, student)

    response = client.get(f"/calendar/courses/{course.id}.ics")
    assert response.status_code == 200
    assert response.mimetype == "text/calendar"
    assert response.headers["Content-Disposition"] == 'attachment; filename="CS101-Fall-2026.ics"'

    text = response.get_data(as_text=True)
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    assert "SUMMARY:Midterm\\, part 1" in text
    assert "DTSTART:20261203T100000" in text and "DTEND:20261203T120000" in text
    assert "RRULE:FREQ=WEEKLY;COUNT=15" in text and "SUMMARY:CS101 class" in text
    assert text.count("BEGIN:VEVENT") == 2


def test_ics_has_only_my_own_classes(client, student, classmate, course):
    db.session.add(ClassSlot(user=classmate, course=course, weekday=1, start_time=time(9),
                             end_time=time(10)))
    db.session.commit()
    log_in(client, student)
    assert "BEGIN:VEVENT" not in client.get(f"/calendar/courses/{course.id}.ics").get_data(as_text=True)


def test_ics_needs_login_and_a_real_course(client, student):
    assert client.get("/calendar/courses/1.ics").status_code == 302
    log_in(client, student)
    assert client.get("/calendar/courses/999.ics").status_code == 404

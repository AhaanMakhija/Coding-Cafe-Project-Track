"""Turning events and class slots into the JSON format FullCalendar reads.

FullCalendar docs: an event is a dict with "title", "start", "end"; a weekly
repeating event uses "daysOfWeek", "startTime" and "endTime" instead.
"""

from datetime import datetime

from flask import url_for


def parse_fc_datetime(value):
    """Parse the ?start= / ?end= values FullCalendar adds to its requests.

    They look like "2026-10-26T00:00:00+05:30". Events are stored as local
    wall-clock times, so the timezone offset is dropped rather than converted.

    Returns None if value is missing. Raises ValueError if it is not a date.
    """
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=None)


def to_fc_weekday(weekday):
    """Our weekday (0 = Monday, like Python) -> FullCalendar's (0 = Sunday).

    Monday 0 -> 1, Tuesday 1 -> 2, ... Saturday 5 -> 6, Sunday 6 -> 0.
    """
    return (weekday + 1) % 7


def event_to_fc(event):
    """One campus event as a FullCalendar event. Clicking it opens the event page."""
    return {
        "id": f"event-{event.id}",
        "title": event.title,
        "start": event.start_at.isoformat(timespec="minutes"),
        "end": event.end_at.isoformat(timespec="minutes"),
        "url": url_for("calendar.event_detail", event_id=event.id),
        "extendedProps": {"layer": "campus", "location": event.location},
    }


def slot_to_fc(slot):
    """One weekly class as a repeating FullCalendar event. Clicking it opens the course."""
    title = slot.course.code + (f" · {slot.room}" if slot.room else "")
    return {
        "id": f"class-{slot.id}",
        "title": title,
        "daysOfWeek": [to_fc_weekday(slot.weekday)],
        "startTime": slot.start_time.strftime("%H:%M"),
        "endTime": slot.end_time.strftime("%H:%M"),
        "url": url_for("resources.course_detail", course_id=slot.course_id),
        "extendedProps": {"layer": "classes", "course": slot.course.name},
    }

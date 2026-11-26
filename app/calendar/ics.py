"""Building .ics files (iCalendar, RFC 5545), the format every calendar app imports.

A file is a VCALENDAR block holding one VEVENT block per event, each line
"NAME:value". Written by hand instead of with a library: the format is plain
text, and these few rules are all ORBIT needs.
"""

from datetime import date, datetime, timedelta, timezone

# Weekly classes repeat for about one semester after the download.
CLASS_WEEKS = 15


def escape(text):
    """Escape text for an .ics value: \\ ; , and line breaks have special meanings."""
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
                .replace("\r\n", "\\n").replace("\n", "\\n"))


def fold(line):
    """Split lines longer than 75 bytes; each continuation line starts with a space."""
    data = line.encode("utf-8")
    if len(data) <= 75:
        return line
    parts, start = [], 0
    while start < len(data):
        limit = 75 if start == 0 else 74  # continuation lines lose a byte to the space
        end = min(start + limit, len(data))
        while end < len(data) and (data[end] & 0xC0) == 0x80:
            end -= 1  # never cut a multi-byte character (e.g. "·") in half
        parts.append(data[start:end].decode("utf-8"))
        start = end
    return "\r\n ".join(parts)


def stamp(moment):
    """Local "floating" time: 2026-11-27 15:00 -> 20261127T150000.

    No time zone is attached, so a calendar app shows it at that wall-clock time,
    which is how ORBIT stores times for its single campus.
    """
    return moment.strftime("%Y%m%dT%H%M%S")


def next_weekday(weekday, today):
    """The first date on or after today that falls on weekday (0 = Monday)."""
    return today + timedelta(days=(weekday - today.weekday()) % 7)


def event_lines(event, now):
    lines = [
        "BEGIN:VEVENT",
        f"UID:event-{event.id}@orbit",
        f"DTSTAMP:{now:%Y%m%dT%H%M%SZ}",
        f"DTSTART:{stamp(event.start_at)}",
        f"DTEND:{stamp(event.end_at)}",
        f"SUMMARY:{escape(event.title)}",
    ]
    if event.location:
        lines.append(f"LOCATION:{escape(event.location)}")
    if event.description:
        lines.append(f"DESCRIPTION:{escape(event.description)}")
    return lines + ["END:VEVENT"]


def class_lines(slot, now, today):
    first = next_weekday(slot.weekday, today)
    lines = [
        "BEGIN:VEVENT",
        f"UID:class-{slot.id}@orbit",
        f"DTSTAMP:{now:%Y%m%dT%H%M%SZ}",
        f"DTSTART:{stamp(datetime.combine(first, slot.start_time))}",
        f"DTEND:{stamp(datetime.combine(first, slot.end_time))}",
        f"RRULE:FREQ=WEEKLY;COUNT={CLASS_WEEKS}",  # repeat every week
        f"SUMMARY:{escape(slot.course.code + ' class')}",
    ]
    if slot.room:
        lines.append(f"LOCATION:{escape('Room ' + slot.room)}")
    return lines + ["END:VEVENT"]


def course_calendar(course, events, class_slots, today=None):
    """The whole .ics file for a course: its events plus the viewer's weekly classes."""
    now = datetime.now(timezone.utc)
    today = today or date.today()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ORBIT//Course calendar//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{escape(f'{course.code} · {course.name}')}",  # the calendar's name in Google/Apple
    ]
    for event in events:
        lines += event_lines(event, now)
    for slot in class_slots:
        lines += class_lines(slot, now, today)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"

"""Small Jinja filters used across templates. Registered in create_app()."""

from datetime import datetime, timezone


def plural(count, word, plural_word=None):
    """{{ 3 | plural("file") }} -> "3 files"; {{ 1 | plural("file") }} -> "1 file".

    Irregular words pass their plural: {{ n | plural("class", "classes") }}.
    """
    return f"{count} {word}" if count == 1 else f"{count} {plural_word or word + 's'}"


def timeago(moment, now=None):
    """How long ago a UTC timestamp was: "just now", "5 minutes ago", "3 days ago".

    created_at columns are stored in UTC. Showing "2 hours ago" instead of a clock
    time avoids converting to each viewer's timezone. SQLite gives back naive
    datetimes, so a naive value is treated as UTC.
    """
    if moment is None:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    seconds = int(((now or datetime.now(timezone.utc)) - moment).total_seconds())

    if seconds < 60:
        return "just now"
    for size, unit in ((365 * 86400, "year"), (30 * 86400, "month"), (7 * 86400, "week"),
                       (86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size:
            return f"{plural(seconds // size, unit)} ago"


def register(app):
    app.add_template_filter(plural, "plural")
    app.add_template_filter(timeago, "timeago")

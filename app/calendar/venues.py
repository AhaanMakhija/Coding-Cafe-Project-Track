"""Venue booking rule: two events can't use the same venue at overlapping times.

The rule holds across all accounts, because every event is checked against the
whole database, not just the current user's events.
"""

from sqlalchemy import func

from app.extensions import db
from app.models import Event


def find_clash(location, start_at, end_at, exclude_id=None):
    """Return an event already at this venue overlapping start_at-end_at, or None.

    Venue names match ignoring capitals ("room 204" = "Room 204"); the form has
    already squeezed repeated spaces. Two events overlap when each starts before
    the other ends, so back-to-back bookings (one ends at 3:00, the next starts
    at 3:00) are fine.
    """
    query = db.select(Event).where(
        func.lower(Event.location) == location.lower(),
        Event.start_at < end_at,
        Event.end_at > start_at,
    )
    if exclude_id is not None:
        query = query.where(Event.id != exclude_id)  # editing an event doesn't clash with itself
    return db.session.scalar(query.order_by(Event.start_at).limit(1))

"""Searching and filtering a course's resources.

Kept apart from the routes: the route only reads the URL, and this module
builds the database query, so each part can be tested on its own.
"""

from dataclasses import dataclass

from app.extensions import db
from app.models import RESOURCE_TYPES, Resource

OFFICIAL_CHOICES = ("official", "unofficial")


@dataclass
class ResourceFilters:
    """What the user asked for. Empty strings mean "don't filter on this"."""

    q: str = ""
    type: str = ""
    official: str = ""

    @classmethod
    def from_args(cls, args):
        """Read ?q=&type=&official= from the URL, ignoring values we don't recognise.

        A hand-edited URL like ?type=meme just shows everything instead of an error.
        """
        q = (args.get("q") or "").strip()[:100]
        rtype = args.get("type", "")
        official = args.get("official", "")
        return cls(
            q=q,
            type=rtype if rtype in RESOURCE_TYPES else "",
            official=official if official in OFFICIAL_CHOICES else "",
        )

    @property
    def active(self):
        return bool(self.q or self.type or self.official)


def filter_resources(course, filters):
    """Return the course's resources that match filters, newest first."""
    query = db.select(Resource).filter_by(course_id=course.id)

    if filters.q:
        # Case-insensitive "contains" on title or tags. autoescape=True makes
        # % and _ in the search box literal characters instead of SQL wildcards.
        query = query.where(
            Resource.title.icontains(filters.q, autoescape=True)
            | Resource.tags.icontains(filters.q, autoescape=True)
        )
    if filters.type:
        query = query.filter_by(type=filters.type)
    if filters.official:
        query = query.filter_by(is_official=(filters.official == "official"))

    return db.session.scalars(query.order_by(Resource.created_at.desc(), Resource.id.desc())).all()

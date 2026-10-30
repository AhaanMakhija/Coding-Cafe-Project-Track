"""Database tables for ORBIT.

Course is the hub: users enrol in courses, and (later) resources, class slots
and forum threads all belong to a course.
"""

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager

ROLES = ("student", "staff")
RESOURCE_KINDS = ("file", "link")
RESOURCE_TYPES = ("notes", "slides", "past paper", "assignment", "other")


def utc_now():
    """Current time in UTC, used as the default for created_at columns."""
    return datetime.now(timezone.utc)

# Many-to-many link between users and courses. It has no fields of its own,
# so it is a plain table rather than a model class.
enrollment = db.Table(
    "enrollment",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("course_id", db.Integer, db.ForeignKey("course.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    """A student or staff member who can sign in."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="student")

    courses = db.relationship("Course", secondary=enrollment, back_populates="students")
    resources = db.relationship("Resource", back_populates="uploader")
    class_slots = db.relationship("ClassSlot", back_populates="user")

    @validates("role")
    def validate_role(self, key, value):
        if value not in ROLES:
            raise ValueError(f"role must be one of {ROLES}, got {value!r}")
        return value

    @validates("email")
    def normalise_email(self, key, value):
        # Store emails lower-case so "Ahaan@X.com" and "ahaan@x.com" are one account.
        return value.strip().lower()

    @property
    def is_staff(self):
        return self.role == "staff"

    def set_password(self, password):
        """Hash and store a password; the plain text is never saved."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login stores only the user's id in the session cookie; this turns it back into a User."""
    return db.session.get(User, int(user_id))


class Course(db.Model):
    """A course that users enrol in, e.g. CS101, Intro to Programming, Fall 2026."""

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    term = db.Column(db.String(30), nullable=False)

    students = db.relationship("User", secondary=enrollment, back_populates="courses")
    resources = db.relationship("Resource", back_populates="course")
    class_slots = db.relationship("ClassSlot", back_populates="course")
    threads = db.relationship(
        "Thread", back_populates="course", order_by="Thread.created_at.desc()"
    )

    # The same code can run in different terms, but not twice in one term.
    __table_args__ = (db.UniqueConstraint("code", "term"),)

    def __repr__(self):
        return f"<Course {self.code} {self.term}>"


class Resource(db.Model):
    """A study resource in a course: either an uploaded file or a saved link."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    file_path = db.Column(db.String(300))  # set when kind == "file"
    url = db.Column(db.String(500))  # set when kind == "link"
    type = db.Column(db.String(20), nullable=False, default="other")
    tags = db.Column(db.String(200), nullable=False, default="")  # comma-separated
    is_official = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course = db.relationship("Course", back_populates="resources")
    uploader = db.relationship("User", back_populates="resources")

    # Enforced by the database itself: a file has a path and no URL, a link the opposite.
    __table_args__ = (
        db.CheckConstraint(
            "(kind = 'file' AND file_path IS NOT NULL AND url IS NULL)"
            " OR (kind = 'link' AND url IS NOT NULL AND file_path IS NULL)",
            name="file_xor_link",
        ),
    )

    @validates("kind")
    def validate_kind(self, key, value):
        if value not in RESOURCE_KINDS:
            raise ValueError(f"kind must be one of {RESOURCE_KINDS}, got {value!r}")
        return value

    @validates("type")
    def validate_type(self, key, value):
        if value not in RESOURCE_TYPES:
            raise ValueError(f"type must be one of {RESOURCE_TYPES}, got {value!r}")
        return value

    @property
    def tag_list(self):
        """Tags as a clean list, e.g. "midterm, Week 3 ," -> ["midterm", "week 3"]."""
        return [tag.strip().lower() for tag in self.tags.split(",") if tag.strip()]

    def __repr__(self):
        return f"<Resource {self.title!r} ({self.kind})>"


class Event(db.Model):
    """A one-off campus event posted by staff, shown on everyone's calendar.

    Named start_at/end_at because END is a reserved word in SQL; the calendar
    API will send them to FullCalendar as "start" and "end".
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(120), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")

    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    creator = db.relationship("User")

    __table_args__ = (db.CheckConstraint("end_at > start_at", name="event_ends_after_start"),)

    def __repr__(self):
        return f"<Event {self.title!r} {self.start_at:%Y-%m-%d %H:%M}>"


class ClassSlot(db.Model):
    """One weekly class in a user's own timetable, e.g. CS101 every Monday 10:00-11:30.

    It stores the weekday and times only; FullCalendar repeats it every week.
    """

    id = db.Column(db.Integer, primary_key=True)
    weekday = db.Column(db.Integer, nullable=False)  # 0 = Monday ... 6 = Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(50), nullable=False, default="")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    user = db.relationship("User", back_populates="class_slots")
    course = db.relationship("Course", back_populates="class_slots")

    __table_args__ = (
        db.CheckConstraint("weekday BETWEEN 0 AND 6", name="valid_weekday"),
        db.CheckConstraint("end_time > start_time", name="slot_ends_after_start"),
    )

    def __repr__(self):
        return f"<ClassSlot day={self.weekday} {self.start_time}-{self.end_time}>"


class Thread(db.Model):
    """A discussion topic on a course's board; replies are Posts."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course = db.relationship("Course", back_populates="threads")
    author = db.relationship("User")

    # Replies read top to bottom, oldest first. Deleting a thread deletes its replies.
    posts = db.relationship(
        "Post", back_populates="thread", order_by="Post.created_at",
        cascade="all, delete-orphan",
    )

    @property
    def reply_count(self):
        return len(self.posts)

    def __repr__(self):
        return f"<Thread {self.title!r}>"


class Post(db.Model):
    """A reply in a thread, optionally with one attached file.

    The attachment is a Resource, so forum uploads reuse the library's upload
    code and safety checks instead of duplicating them.
    """

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    thread_id = db.Column(db.Integer, db.ForeignKey("thread.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    attachment_resource_id = db.Column(db.Integer, db.ForeignKey("resource.id"))
    thread = db.relationship("Thread", back_populates="posts")
    author = db.relationship("User")
    attachment = db.relationship("Resource")

    def __repr__(self):
        return f"<Post {self.id} in thread {self.thread_id}>"

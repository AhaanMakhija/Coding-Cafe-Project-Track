"""Database tables for ORBIT.

Course is the hub: users enrol in courses, and (later) resources, class slots
and forum threads all belong to a course.
"""

from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

ROLES = ("student", "staff")

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


class Course(db.Model):
    """A course that users enrol in, e.g. CS101, Intro to Programming, Fall 2026."""

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    term = db.Column(db.String(30), nullable=False)

    students = db.relationship("User", secondary=enrollment, back_populates="courses")

    # The same code can run in different terms, but not twice in one term.
    __table_args__ = (db.UniqueConstraint("code", "term"),)

    def __repr__(self):
        return f"<Course {self.code} {self.term}>"

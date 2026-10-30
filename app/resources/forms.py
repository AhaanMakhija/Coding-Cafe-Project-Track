"""Forms for courses and resources."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

from app.auth.forms import strip_spaces
from app.extensions import db
from app.models import Course


def to_upper(value):
    """Course codes are stored upper-case so "cs101" and "CS101" are the same course."""
    return value.upper() if isinstance(value, str) else value


class CourseForm(FlaskForm):
    code = StringField("Course code", filters=[strip_spaces, to_upper],
                       validators=[DataRequired(), Length(max=20)])
    name = StringField("Course name", filters=[strip_spaces],
                       validators=[DataRequired(), Length(max=120)])
    term = StringField("Term", filters=[strip_spaces],
                       validators=[DataRequired(), Length(max=30)],
                       description="For example: Fall 2026")
    submit = SubmitField("Create course")

    def validate_code(self, field):
        # Checked here too (not only by the database) so the user sees a clear message.
        exists = db.session.scalar(
            db.select(Course).filter_by(code=field.data, term=self.term.data)
        )
        if exists:
            raise ValidationError(f"{field.data} already exists for {self.term.data}.")

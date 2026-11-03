"""Forms for campus events and weekly class slots."""

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField, SelectChoice, SelectField, StringField, SubmitField, TextAreaField, TimeField,
)
from wtforms.validators import DataRequired, Length, ValidationError

from app.auth.forms import strip_spaces
from app.models import WEEKDAYS

# The format browsers send from <input type="datetime-local">, e.g. 2026-11-07T10:30.
DATETIME_LOCAL = "%Y-%m-%dT%H:%M"


class EventForm(FlaskForm):
    title = StringField("Title", filters=[strip_spaces],
                        validators=[DataRequired(), Length(max=200)])
    start_at = DateTimeLocalField("Starts", format=DATETIME_LOCAL, validators=[DataRequired()])
    end_at = DateTimeLocalField("Ends", format=DATETIME_LOCAL, validators=[DataRequired()])
    location = StringField("Location", filters=[strip_spaces], validators=[Length(max=120)],
                           description="For example: Main auditorium")
    description = TextAreaField("Description", filters=[strip_spaces],
                                validators=[Length(max=2000)])
    submit = SubmitField("Save event")

    def validate_end_at(self, field):
        if self.start_at.data and field.data and field.data <= self.start_at.data:
            raise ValidationError("The event must end after it starts.")


class ClassSlotForm(FlaskForm):
    # Choices depend on who is logged in, so the route fills them in.
    course_id = SelectField("Course", coerce=int, validators=[DataRequired()])
    weekday = SelectField("Day", coerce=int,
                          choices=[SelectChoice(i, name) for i, name in enumerate(WEEKDAYS)])
    start_time = TimeField("Starts", validators=[DataRequired()])
    end_time = TimeField("Ends", validators=[DataRequired()])
    room = StringField("Room", filters=[strip_spaces], validators=[Length(max=50)],
                       description="For example: 204")
    submit = SubmitField("Add class")

    def validate_end_time(self, field):
        if self.start_time.data and field.data and field.data <= self.start_time.data:
            raise ValidationError("The class must end after it starts.")

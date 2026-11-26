"""Forms for events and weekly class slots."""

from datetime import datetime, time

from flask_wtf import FlaskForm
from wtforms import DateField, SelectChoice, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from app.auth.forms import strip_spaces
from app.calendar.venues import find_clash
from app.models import WEEKDAYS
from app.template_filters import clock

CAMPUS = 0  # course_id value meaning "campus-wide, no course"


def to_time(value):
    """"14:30" -> time(14, 30). Times already parsed (e.g. when editing) pass through."""
    if isinstance(value, time) or value is None:
        return value
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


# Every 15 minutes of the day, shown with AM/PM: ("14:30", "2:30 PM").
# A dropdown instead of <input type="time">, whose look and 12/24-hour format
# depend on each computer's region settings (some show no AM/PM at all).
TIME_CHOICES = [SelectChoice(f"{h:02d}:{m:02d}", clock(time(h, m)))
                for h in range(24) for m in (0, 15, 30, 45)]


class TimeSelectField(SelectField):
    """A time picked from TIME_CHOICES; .data is a datetime.time."""

    def __init__(self, label, **kwargs):
        super().__init__(label, choices=TIME_CHOICES, coerce=to_time, **kwargs)


def collapse_spaces(value):
    """"  Room   204 " -> "Room 204", so venue names compare cleanly."""
    return " ".join(value.split()) if isinstance(value, str) else value


class EventForm(FlaskForm):
    title = StringField("Title", filters=[strip_spaces],
                        validators=[DataRequired(), Length(max=200)])
    # Choices depend on who is logged in (staff can post campus-wide), so the route fills them in.
    course_id = SelectField("Calendar", coerce=int)
    day = DateField("Date", validators=[DataRequired(message="Pick a date.")])
    start_time = TimeSelectField("Starts", default=time(9))
    end_time = TimeSelectField("Ends", default=time(10))
    location = StringField("Venue", filters=[collapse_spaces], validators=[Length(max=120)],
                           description="Two events can't use the same venue at the same time.")
    description = TextAreaField("Description", filters=[strip_spaces],
                                validators=[Length(max=2000)])
    submit = SubmitField("Save event")

    def __init__(self, *args, event_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_id = event_id  # when editing, the event doesn't clash with itself

    def validate_end_time(self, field):
        if self.start_time.data and field.data and field.data <= self.start_time.data:
            raise ValidationError("The event must end after it starts.")

    def validate_location(self, field):
        start, end = self.start_at, self.end_at
        if not (field.data and start and end and end > start):
            return  # no venue, or the times are already wrong
        clash = find_clash(field.data, start, end, exclude_id=self.event_id)
        if clash:
            raise ValidationError(
                f"{clash.location} is already booked for “{clash.title}” "
                f"({clash.start_at:%d %b}, {clock(clash.start_at)}–{clock(clash.end_at)}). "
                "Pick another time or venue."
            )

    @property
    def start_at(self):
        """The date and start time joined into one datetime (None if either is missing)."""
        if self.day.data and self.start_time.data:
            return datetime.combine(self.day.data, self.start_time.data)

    @property
    def end_at(self):
        if self.day.data and self.end_time.data:
            return datetime.combine(self.day.data, self.end_time.data)


class ClassSlotForm(FlaskForm):
    # Choices depend on who is logged in, so the route fills them in.
    course_id = SelectField("Course", coerce=int, validators=[DataRequired()])
    weekday = SelectField("Day", coerce=int,
                          choices=[SelectChoice(i, name) for i, name in enumerate(WEEKDAYS)])
    start_time = TimeSelectField("Starts", default=time(9))
    end_time = TimeSelectField("Ends", default=time(10))
    room = StringField("Room", filters=[strip_spaces], validators=[Length(max=50)],
                       description="For example: 204")
    submit = SubmitField("Add class")

    def validate_end_time(self, field):
        if self.start_time.data and field.data and field.data <= self.start_time.data:
            raise ValidationError("The class must end after it starts.")

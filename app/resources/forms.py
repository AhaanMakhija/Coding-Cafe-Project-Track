"""Forms for courses and resources."""

from urllib.parse import urlsplit

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import RadioField, SelectChoice, SelectField, StringField, SubmitField, URLField
from wtforms.validators import DataRequired, Length, ValidationError

from app.auth.forms import strip_spaces
from app.extensions import db
from app.models import RESOURCE_TYPES, Course
from app.resources.storage import ALLOWED_EXTENSIONS


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


class ResourceForm(FlaskForm):
    """One form for both kinds of resource; `kind` decides which field is required."""

    title = StringField("Title", filters=[strip_spaces],
                        validators=[DataRequired(), Length(max=200)])
    kind = RadioField("Add a", choices=[SelectChoice("file", "File upload"),
                                        SelectChoice("link", "Link")],
                      default="file", validators=[DataRequired()])
    file = FileField("File", validators=[
        FileAllowed(ALLOWED_EXTENSIONS, "Allowed types: PDF, DOCX, PPTX, PNG, JPG."),
    ], description="Max 10 MB.")
    # No Optional() here: it would skip validate_url when the box is empty.
    url = URLField("Link", filters=[strip_spaces], validators=[Length(max=500)],
                   description="Google Drive, OneDrive, YouTube or any web page.")
    # Named resource_type, not type, to avoid shadowing Python's built-in type().
    resource_type = SelectField("Type", choices=[SelectChoice(t, t.capitalize()) for t in RESOURCE_TYPES],
                                default="notes")
    tags = StringField("Tags", filters=[strip_spaces], validators=[Length(max=200)],
                       description="Comma-separated, e.g. midterm, week 3")
    submit = SubmitField("Add resource")

    def validate_file(self, field):
        if self.kind.data == "file" and not field.data:
            raise ValidationError("Choose a file to upload.")

    def validate_url(self, field):
        if self.kind.data != "link":
            return
        if not field.data:
            raise ValidationError("Enter a link.")
        # Only web links. This blocks "javascript:..." links, which would run
        # code in the browser of whoever clicks them.
        parts = urlsplit(field.data)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValidationError("Enter a full link starting with http:// or https://")

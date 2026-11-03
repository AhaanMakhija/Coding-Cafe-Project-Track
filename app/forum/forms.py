"""Forms for starting a thread and replying to one."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.auth.forms import strip_spaces
from app.resources.storage import ALLOWED_EXTENSIONS


class ThreadForm(FlaskForm):
    title = StringField("Title", filters=[strip_spaces],
                        validators=[DataRequired(), Length(max=200)],
                        description="A clear question gets better answers, e.g. “Lab 2, question 3: why does my loop never end?”")
    body = TextAreaField("Details", filters=[strip_spaces],
                         validators=[DataRequired(), Length(max=5000)])
    submit = SubmitField("Start thread")


class ReplyForm(FlaskForm):
    body = TextAreaField("Your reply", filters=[strip_spaces],
                         validators=[DataRequired(), Length(max=5000)])
    # Same allow-list as the library, because attachments are saved by the same code.
    file = FileField("Attach a file (optional)", validators=[
        FileAllowed(ALLOWED_EXTENSIONS, "Allowed types: PDF, DOCX, PPTX, PNG, JPG."),
    ])
    submit = SubmitField("Post reply")

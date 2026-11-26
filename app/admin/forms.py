"""The form an admin uses to change an account."""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SelectChoice, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app.auth.forms import strip_spaces
from app.extensions import db
from app.models import ROLES, User


class EditUserForm(FlaskForm):
    name = StringField("Name", filters=[strip_spaces], validators=[DataRequired(), Length(max=100)])
    email = EmailField("Email", filters=[strip_spaces],
                       validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField("Role", choices=[SelectChoice(r, r.capitalize()) for r in ROLES])
    # Optional(): leave it empty to keep the current password.
    new_password = PasswordField("Set a new password", validators=[
        Optional(), Length(min=8, max=128, message="Password must be at least 8 characters."),
    ])
    submit = SubmitField("Save changes")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user  # the account being edited

    def validate_email(self, field):
        taken = db.session.scalar(db.select(User).filter_by(email=field.data.lower()))
        if taken and taken.id != self.user.id:
            raise ValidationError("Another account already uses this email.")

    def validate_role(self, field):
        # Someone must always be able to manage accounts.
        if self.user.is_admin and field.data != "admin":
            admins = db.session.scalar(db.select(db.func.count()).select_from(User).filter_by(role="admin"))
            if admins == 1:
                raise ValidationError("This is the only admin. Make someone else an admin first.")

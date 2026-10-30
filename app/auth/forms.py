"""Forms for the accounts pages. Flask-WTF validates input and adds a CSRF token."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.extensions import db
from app.models import User


def strip_spaces(value):
    """Filter that removes spaces pasted around an input before it is validated."""
    return value.strip() if isinstance(value, str) else value


class SignupForm(FlaskForm):
    name = StringField("Name", filters=[strip_spaces], validators=[DataRequired(), Length(max=100)])
    email = EmailField(
        "Email", filters=[strip_spaces], validators=[DataRequired(), Email(), Length(max=120)]
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=128, message="Password must be at least 8 characters."),
        ],
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Sign up")

    def validate_email(self, field):
        """WTForms runs validate_<fieldname> automatically after the built-in checks."""
        if db.session.scalar(db.select(User).filter_by(email=field.data.lower())):
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = EmailField("Email", filters=[strip_spaces], validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me logged in")
    submit = SubmitField("Log in")

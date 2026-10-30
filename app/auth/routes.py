"""Routes for the accounts Blueprint. All URLs here start with /auth."""

from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm, SignupForm
from app.extensions import db
from app.models import User


def is_safe_next_url(target):
    """Allow only links back into this site, e.g. "/auth/profile".

    Without this check, a link like /auth/login?next=https://evil.example could
    send someone to a fake site straight after they log in (an "open redirect").
    """
    if not target:
        return False
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc and target.startswith("/")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = SignupForm()
    if form.validate_on_submit():
        # Everyone signs up as a student; staff accounts are promoted separately.
        user = User(name=form.name.data, email=form.email.data, role="student")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Welcome to ORBIT! Your account is ready.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/signup.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = db.session.scalar(db.select(User).filter_by(email=email))

        # Same message for a wrong email and a wrong password, so the form does
        # not reveal which emails have accounts.
        if user is None or not user.check_password(form.password.data):
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", form=form), 401

        login_user(user, remember=form.remember.data)
        next_url = request.args.get("next")
        return redirect(next_url if is_safe_next_url(next_url) else url_for("auth.profile"))

    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    # POST only, so a link or image on another site cannot log people out.
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html", user=current_user)

"""Routes for the admin pages. All URLs here start with /admin."""

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from app.admin import bp
from app.admin.forms import EditUserForm
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import ROLES, Event, Post, Thread, User


def activity(user):
    """How much each account has done, for the details page."""
    def count(model, column):
        return db.session.scalar(db.select(func.count()).select_from(model).where(column == user.id))
    return {
        "Resources added": len(user.resources),
        "Threads started": count(Thread, Thread.author_id),
        "Replies posted": count(Post, Post.author_id),
        "Events added": count(Event, Event.creator_id),
        "Weekly classes": len(user.class_slots),
    }


@bp.route("/")
@admin_required
def users():
    """Every account, with search by name or email and a role filter."""
    q = (request.args.get("q") or "").strip()[:100]
    role = request.args.get("role", "")
    query = db.select(User)
    if q:
        query = query.where(or_(User.name.icontains(q, autoescape=True),
                                User.email.icontains(q, autoescape=True)))
    if role in ROLES:
        query = query.filter_by(role=role)
    accounts = db.session.scalars(query.order_by(User.role, User.name)).all()
    totals = dict(db.session.execute(db.select(User.role, func.count()).group_by(User.role)).all())
    return render_template("admin/users.html", accounts=accounts, q=q, role=role,
                           roles=ROLES, totals=totals)


@bp.route("/users/<int:user_id>", methods=["GET", "POST"])
@admin_required
def user_detail(user_id):
    user = db.get_or_404(User, user_id)
    form = EditUserForm(user=user, data={"name": user.name, "email": user.email, "role": user.role})

    if form.validate_on_submit():
        changes = []
        if form.name.data != user.name:
            user.name = form.name.data
            changes.append("name")
        if form.email.data.lower() != user.email:
            user.email = form.email.data  # the model lower-cases it
            changes.append("email")
        if form.role.data != user.role:
            user.role = form.role.data
            changes.append(f"role (now {user.role})")
        if form.new_password.data:
            user.set_password(form.new_password.data)
            changes.append("password")
        db.session.commit()

        flash(f"Updated {user.name}: {', '.join(changes)}." if changes else "Nothing changed.",
              "success" if changes else "info")
        return redirect(url_for("admin.user_detail", user_id=user.id))

    return render_template("admin/user_detail.html", user=user, form=form, activity=activity(user))

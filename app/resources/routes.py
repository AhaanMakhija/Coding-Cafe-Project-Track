"""Routes for courses and enrollment. All URLs here start with /courses."""

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.auth.decorators import staff_required
from app.extensions import db
from app.models import Course
from app.resources import bp
from app.resources.forms import CourseForm


@bp.route("/")
@login_required
def course_list():
    courses = db.session.scalars(db.select(Course).order_by(Course.code, Course.term)).all()
    return render_template("resources/course_list.html", courses=courses)


@bp.route("/new", methods=["GET", "POST"])
@staff_required
def new_course():
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(code=form.code.data, name=form.name.data, term=form.term.data)
        db.session.add(course)
        db.session.commit()
        flash(f"Created {course.code}.", "success")
        return redirect(url_for("resources.course_detail", course_id=course.id))
    return render_template("resources/course_form.html", form=form)


@bp.route("/<int:course_id>")
@login_required
def course_detail(course_id):
    course = db.get_or_404(Course, course_id)
    return render_template("resources/course_detail.html", course=course)


# Join and leave change data, so they are POST-only (like logout).

@bp.route("/<int:course_id>/join", methods=["POST"])
@login_required
def join_course(course_id):
    course = db.get_or_404(Course, course_id)
    if course not in current_user.courses:
        current_user.courses.append(course)
        db.session.commit()
        flash(f"You joined {course.code}.", "success")
    return redirect(url_for("resources.course_detail", course_id=course.id))


@bp.route("/<int:course_id>/leave", methods=["POST"])
@login_required
def leave_course(course_id):
    course = db.get_or_404(Course, course_id)
    if course in current_user.courses:
        current_user.courses.remove(course)
        db.session.commit()
        flash(f"You left {course.code}.", "info")
    return redirect(url_for("resources.course_detail", course_id=course.id))

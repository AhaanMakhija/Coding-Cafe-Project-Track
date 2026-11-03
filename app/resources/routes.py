"""Routes for courses, enrollment and resources. All URLs here start with /courses."""

from flask import (
    abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.auth.decorators import staff_required
from app.extensions import db
from app.models import RESOURCE_TYPES, Course, Post, Resource, split_tags
from app.permissions import can_delete_resource, can_edit_resource, can_participate
from app.resources import bp
from app.resources.forms import CourseForm, EditResourceForm, ResourceForm
from app.resources.queries import ResourceFilters, filter_resources
from app.resources.storage import delete_upload, file_extension, save_upload


def get_course_resource_or_404(course_id, resource_id):
    """Load a resource and make sure it really belongs to the course in the URL."""
    resource = db.get_or_404(Resource, resource_id)
    if resource.course_id != course_id:
        abort(404)
    return resource


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
    filters = ResourceFilters.from_args(request.args)
    return render_template(
        "resources/course_detail.html", course=course,
        resources=filter_resources(course, filters), filters=filters,
        resource_types=RESOURCE_TYPES,
        can_add=can_participate(current_user, course),
        can_edit=can_edit_resource, can_delete=can_delete_resource,
    )


@bp.route("/<int:course_id>/resources/new", methods=["GET", "POST"])
@login_required
def new_resource(course_id):
    course = db.get_or_404(Course, course_id)
    if not can_participate(current_user, course):
        abort(403)

    form = ResourceForm()
    # /resources/new?kind=link opens the form with "Link" already selected
    # (used by the "file too large" page).
    if request.method == "GET" and request.args.get("kind") == "link":
        form.kind.data = "link"

    if form.validate_on_submit():
        resource = Resource(
            title=form.title.data,
            kind=form.kind.data,
            type=form.resource_type.data,
            tags=", ".join(split_tags(form.tags.data)),
            is_official=current_user.is_staff,  # staff uploads are official
            course=course,
            uploader=current_user,
        )
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        if form.kind.data == "file":
            resource.file_path = save_upload(form.file.data, upload_folder)
        else:
            resource.url = form.url.data

        db.session.add(resource)
        try:
            db.session.commit()
        except Exception:
            # Don't leave a file on disk that no database row points to.
            db.session.rollback()
            if resource.file_path:
                delete_upload(resource.file_path, upload_folder)
            raise

        flash(f"Added “{resource.title}”.", "success")
        return redirect(url_for("resources.course_detail", course_id=course.id))

    return render_template("resources/resource_form.html", form=form, course=course)


@bp.route("/<int:course_id>/resources/<int:resource_id>/download")
@login_required
def download_resource(course_id, resource_id):
    resource = get_course_resource_or_404(course_id, resource_id)
    if resource.kind != "file":
        abort(404)

    # Saved as "<title>.<ext>" instead of the random stored name.
    download_name = f"{secure_filename(resource.title) or 'resource'}.{file_extension(resource.file_path)}"
    # as_attachment=True makes the browser download the file rather than open it,
    # so an uploaded file can never run as a page on our site.
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], resource.file_path,
        as_attachment=True, download_name=download_name,
    )


@bp.route("/<int:course_id>/resources/<int:resource_id>/edit", methods=["GET", "POST"])
@login_required
def edit_resource(course_id, resource_id):
    resource = get_course_resource_or_404(course_id, resource_id)
    if not can_edit_resource(current_user, resource):
        abort(403)

    # data= fills the form with the current values on GET; on POST the
    # submitted values take over.
    form = EditResourceForm(is_link=resource.kind == "link", data={
        "title": resource.title, "url": resource.url,
        "resource_type": resource.type, "tags": resource.tags,
    })
    if form.validate_on_submit():
        resource.title = form.title.data
        resource.type = form.resource_type.data
        resource.tags = ", ".join(split_tags(form.tags.data))
        if resource.kind == "link":
            resource.url = form.url.data
        db.session.commit()
        flash(f"Saved changes to “{resource.title}”.", "success")
        return redirect(url_for("resources.course_detail", course_id=course_id))

    return render_template("resources/resource_edit.html", form=form, resource=resource)


@bp.route("/<int:course_id>/resources/<int:resource_id>/delete", methods=["POST"])
@login_required
def delete_resource(course_id, resource_id):
    resource = get_course_resource_or_404(course_id, resource_id)
    if not can_delete_resource(current_user, resource):
        abort(403)

    title, stored_file = resource.title, resource.file_path
    # Forum posts that attached this file keep their text but lose the attachment.
    db.session.execute(
        db.update(Post).where(Post.attachment_resource_id == resource.id)
        .values(attachment_resource_id=None)
    )
    db.session.delete(resource)
    db.session.commit()

    # Remove the file only after the database change succeeded, so a failed
    # delete never leaves a row pointing at a missing file.
    if stored_file:
        delete_upload(stored_file, current_app.config["UPLOAD_FOLDER"])

    flash(f"Deleted “{title}”.", "info")
    return redirect(url_for("resources.course_detail", course_id=course_id))


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

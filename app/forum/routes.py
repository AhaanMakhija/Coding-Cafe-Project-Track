"""Routes for the course boards. All URLs here start with /board."""

import os

from flask import abort, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forum import bp
from app.forum.forms import ReplyForm, ThreadForm
from app.models import Course, Post, Resource, Thread
from app.permissions import can_delete_post, can_participate
from app.resources.storage import delete_upload, save_upload

# Tag given to files attached on a board, so they're findable in the library
# (search "board") and so we know which resources belong to a post.
BOARD_TAG = "board"


def save_attachment(file_storage, thread):
    """Save an uploaded attachment as a Resource in the thread's course.

    This is the library's own upload code (save_upload), so attachments get the
    same file-type allow-list, size limit and random file names.
    """
    original = secure_filename(file_storage.filename or "") or "attachment"
    stored_name = save_upload(file_storage, current_app.config["UPLOAD_FOLDER"])
    return Resource(
        title=os.path.splitext(original)[0],
        kind="file", file_path=stored_name, type="other", tags=BOARD_TAG,
        is_official=current_user.is_staff,
        course=thread.course, uploader=current_user,
    )


def remove_attachment(post):
    """Delete a post's attachment and its file, if the attachment was made for the board."""
    resource = post.attachment
    if resource is None or BOARD_TAG not in resource.tag_list:
        return None  # a library resource someone else owns stays in the library
    post.attachment = None
    db.session.delete(resource)
    return resource.file_path  # the caller deletes the file after committing


def render_thread(thread, form, status=200):
    return render_template(
        "forum/thread.html", thread=thread, form=form,
        can_reply=can_participate(current_user, thread.course),
        can_delete=can_delete_post,
    ), status


# --- Boards and threads ---------------------------------------------------------

@bp.route("/<int:course_id>/")
@login_required
def board(course_id):
    course = db.get_or_404(Course, course_id)
    return render_template("forum/board.html", course=course,
                           can_post=can_participate(current_user, course))


@bp.route("/<int:course_id>/new", methods=["GET", "POST"])
@login_required
def new_thread(course_id):
    course = db.get_or_404(Course, course_id)
    if not can_participate(current_user, course):
        abort(403)

    form = ThreadForm()
    if form.validate_on_submit():
        thread = Thread(title=form.title.data, body=form.body.data, course=course, author=current_user)
        db.session.add(thread)
        db.session.commit()
        flash("Thread started.", "success")
        return redirect(url_for("forum.thread_detail", thread_id=thread.id))
    return render_template("forum/thread_form.html", form=form, course=course)


@bp.route("/threads/<int:thread_id>")
@login_required
def thread_detail(thread_id):
    thread = db.get_or_404(Thread, thread_id)
    return render_thread(thread, ReplyForm())


@bp.route("/threads/<int:thread_id>/reply", methods=["POST"])
@login_required
def reply(thread_id):
    thread = db.get_or_404(Thread, thread_id)
    if not can_participate(current_user, thread.course):
        abort(403)

    form = ReplyForm()
    if not form.validate_on_submit():
        # Show the thread again with the errors and the text they typed.
        return render_thread(thread, form, status=400)

    post = Post(body=form.body.data, thread=thread, author=current_user)
    if form.file.data:
        post.attachment = save_attachment(form.file.data, thread)
    db.session.add(post)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if post.attachment:
            delete_upload(post.attachment.file_path, current_app.config["UPLOAD_FOLDER"])
        raise

    # #post-<id> scrolls the page to the new reply.
    return redirect(url_for("forum.thread_detail", thread_id=thread.id, _anchor=f"post-{post.id}"))


# --- Deleting (author or staff) --------------------------------------------------

@bp.route("/threads/<int:thread_id>/delete", methods=["POST"])
@login_required
def delete_thread(thread_id):
    thread = db.get_or_404(Thread, thread_id)
    if not can_delete_post(current_user, thread):
        abort(403)

    course_id = thread.course_id
    files = [remove_attachment(post) for post in thread.posts]
    db.session.delete(thread)  # replies are deleted with it (cascade on Thread.posts)
    db.session.commit()
    for stored in filter(None, files):
        delete_upload(stored, current_app.config["UPLOAD_FOLDER"])

    flash("Thread deleted.", "info")
    return redirect(url_for("forum.board", course_id=course_id))


@bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.get_or_404(Post, post_id)
    if not can_delete_post(current_user, post):
        abort(403)

    thread_id = post.thread_id
    stored = remove_attachment(post)
    db.session.delete(post)
    db.session.commit()
    if stored:
        delete_upload(stored, current_app.config["UPLOAD_FOLDER"])

    flash("Reply deleted.", "info")
    return redirect(url_for("forum.thread_detail", thread_id=thread_id))

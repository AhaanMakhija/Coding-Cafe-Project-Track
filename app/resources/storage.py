"""Saving uploaded files to disk safely.

Kept separate from the routes so the forum can reuse it for attachments, and
so the rules (allowed types, random names) are tested in one place.
"""

import os
import uuid

from werkzeug.utils import secure_filename

# Only document and image types. Anything that could run in a browser or on the
# server (.html, .svg, .exe, .py, ...) is refused.
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "png", "jpg", "jpeg"}


def file_extension(filename):
    """Lower-case extension without the dot: "Notes.PDF" -> "pdf", "notes" -> ""."""
    _, ext = os.path.splitext(filename or "")
    return ext[1:].lower()


def is_allowed_file(filename):
    return file_extension(filename) in ALLOWED_EXTENSIONS


def save_upload(file_storage, upload_folder):
    """Save an uploaded file under a new random name and return that name.

    The user's filename is never used as the path: names like "../../app.py"
    could escape the uploads folder, and two people uploading "notes.pdf" would
    overwrite each other. A random UUID avoids both.

    Raises:
        ValueError: if the file type is not allowed.
    """
    original = secure_filename(file_storage.filename or "")
    if not is_allowed_file(original):
        raise ValueError(f"File type not allowed: {file_storage.filename!r}")

    stored_name = f"{uuid.uuid4().hex}.{file_extension(original)}"
    os.makedirs(upload_folder, exist_ok=True)
    file_storage.save(os.path.join(upload_folder, stored_name))
    return stored_name


def delete_upload(stored_name, upload_folder):
    """Remove a stored file if it exists (used when saving to the database fails)."""
    path = os.path.join(upload_folder, stored_name)
    if os.path.isfile(path):
        os.remove(path)

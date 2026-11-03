"""Who is allowed to do what. Every Blueprint and template uses these, so the rules live in one place.

Staff-only pages use the @staff_required decorator in app/auth/decorators.py;
the rules here are the ones that depend on a specific course, resource or post.
"""


def can_participate(user, course):
    """Add resources or post on the board: students must join the course first; staff can always."""
    return user.is_staff or course in user.courses


def can_edit_resource(user, resource):
    """Only the person who added a resource can change its details."""
    return resource.uploader_id == user.id


def can_delete_resource(user, resource):
    """The uploader can delete their own; staff can remove anything (e.g. wrong or copyrighted files)."""
    return resource.uploader_id == user.id or user.is_staff


def can_delete_post(user, post_or_thread):
    """Authors can delete their own threads and replies; staff can moderate any of them."""
    return post_or_thread.author_id == user.id or user.is_staff

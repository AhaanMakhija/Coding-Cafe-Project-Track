"""Route decorators for permission checks shared by every Blueprint."""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def staff_required(view):
    """Allow only staff. Visitors are sent to log in; students get 403 Forbidden.

    Usage:
        @bp.route("/new")
        @staff_required
        def new_course(): ...
    """

    @wraps(view)  # keeps the view's name, which Flask uses for url_for()
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_staff:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Allow only admins. Visitors are sent to log in; everyone else gets 403 Forbidden."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped

"""Session helpers shared by page routes and blueprints."""

from functools import wraps

from flask import redirect, session, url_for


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated

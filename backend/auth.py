"""Session helpers shared by page routes and blueprints."""

from functools import wraps

from flask import flash, redirect, session, url_for

from users_config import USERS


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles: str):
    """Restrict a view to users whose `session['role']` is one of `allowed_roles`."""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in allowed_roles:
                flash("You do not have permission to access this resource.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)

        return decorated

    return decorator


def admin_required(f):
    """Only Admin role."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "Admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated


def investigator_required(f):
    """Admin or Investigator."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ("Admin", "Investigator"):
            flash("Investigator or Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated


def member_allowed(f):
    """Admin, Investigator, or Member (basic user)."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ("Admin", "Investigator", "Member"):
            flash("Access denied.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated


def can_access_evidence(username: str, evidence_id: int, session_user: str) -> bool:
    """Return True if user may view this evidence (role + assignment)."""
    from database import SessionLocal, CaseAssignment, select

    role = USERS.get(username, {}).get("role")
    if role == "Admin":
        return True
    if role == "Investigator":
        with SessionLocal() as db:
            row = db.scalar(
                select(CaseAssignment).where(
                    CaseAssignment.evidence_id == evidence_id,
                    CaseAssignment.assignee_username == username,
                ))
            )
            return row is not None
    if role == "Member":
        with SessionLocal() as db:
            row = db.scalar(
                select(CaseAssignment).where(
                    CaseAssignment.evidence_id == evidence_id,
                    CaseAssignment.assignee_username == username,
                ))
            )
            return row is not None
    return False

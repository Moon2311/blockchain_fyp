"""Session helpers + email/password auth."""

from functools import wraps

from flask import flash, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from sqlalchemy import select

from database import CaseAssignment, SessionLocal, User
from users_config import get_user_by_email, invalidate_users_cache


def _is_api_request() -> bool:
    return request.path.startswith("/api")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            if _is_api_request():
                return jsonify({"error": "Unauthorized", "code": "login_required"}), 401
            return redirect("/")
        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user" not in session:
                if _is_api_request():
                    return jsonify({"error": "Unauthorized", "code": "login_required"}), 401
                return redirect("/")
            if session.get("role") not in allowed_roles:
                if _is_api_request():
                    return jsonify({"error": "Forbidden", "code": "forbidden"}), 403
                flash("You do not have permission to access this resource.", "danger")
                return redirect("/")
            return f(*args, **kwargs)

        return decorated

    return decorator


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            if _is_api_request():
                return jsonify({"error": "Unauthorized", "code": "login_required"}), 401
            return redirect("/")
        if session.get("role") != "Admin":
            if _is_api_request():
                return jsonify({"error": "Forbidden", "code": "admin_required"}), 403
            flash("Admin access required.", "danger")
            return redirect("/")
        return f(*args, **kwargs)

    return decorated


def investigator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            if _is_api_request():
                return jsonify({"error": "Unauthorized"}), 401
            return redirect("/")
        if session.get("role") not in ("Admin", "Investigator"):
            if _is_api_request():
                return jsonify({"error": "Forbidden"}), 403
            flash("Investigator or Admin access required.", "danger")
            return redirect("/")
        return f(*args, **kwargs)

    return decorated


def member_allowed(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            if _is_api_request():
                return jsonify({"error": "Unauthorized"}), 401
            return redirect("/")
        if session.get("role") not in ("Admin", "Investigator", "Member"):
            if _is_api_request():
                return jsonify({"error": "Forbidden"}), 403
            flash("Access denied.", "danger")
            return redirect("/")
        return f(*args, **kwargs)

    return decorated


def can_access_evidence(user_email: str, evidence_id: int) -> bool:
    """Return True if user may view this evidence (Admin: all; others: assignment)."""
    u = get_user_by_email(user_email)
    if u is None:
        return False
    if u.role == "Admin":
        return True
    if u.role not in ("Investigator", "Member"):
        return False
    with SessionLocal() as db:
        row = db.scalar(
            select(CaseAssignment).where(
                CaseAssignment.evidence_id == evidence_id,
                CaseAssignment.assignee_username == u.email,
            )
        )
    return row is not None


def register_user(email: str, password: str, name: str, role: str) -> None:
    """Register a new user with hashed password."""
    if role not in ("Admin", "Investigator", "Member"):
        raise ValueError("Invalid role.")
    pw_hash = generate_password_hash(password)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise ValueError("Email already registered.")
        u = User(
            email=email,
            password_hash=pw_hash,
            name=name,
            role=role,
            is_active=True,
        )
        db.add(u)
        db.commit()
    invalidate_users_cache()


def login_user(email: str, password: str) -> User | None:
    """Validate credentials; return User or None."""
    u = get_user_by_email(email)
    if u is None or not u.is_active:
        return None
    if not check_password_hash(u.password_hash, password):
        return None
    return u

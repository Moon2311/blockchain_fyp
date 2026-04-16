"""Admin-only routes: user management, case assignment, case access requests."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import select

from auth import admin_required, register_user
from database import CaseAccessRequest, CaseAssignment, ForensicCase, SessionLocal, User, utcnow
from users_config import users_dict

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def admin_home():
    return render_template("admin_home.html", users=users_dict())


@admin_bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "Member")
        if not email or not password or not name:
            flash("Email, password, and name are required.", "danger")
        elif role not in ("Admin", "Investigator", "Member"):
            flash("Invalid role.", "danger")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
        else:
            try:
                register_user(email, password, name, role)
                flash(f"User {email} added with role {role}.", "success")
            except ValueError as e:
                flash(str(e), "warning")
    return render_template("admin_users.html", users=users_dict())


@admin_bp.route("/admin/cases/assign", methods=["GET", "POST"])
@admin_required
def admin_assign_cases():
    with SessionLocal() as db:
        cases = db.scalars(select(ForensicCase).order_by(ForensicCase.id.desc())).all()
        user_rows = db.scalars(
            select(User).where(User.role.in_(("Investigator", "Member")))
        ).all()
        assignable_emails = [u.email for u in user_rows]
        assignments = db.scalars(
            select(CaseAssignment).order_by(CaseAssignment.created_at.desc())
        ).all()
    if request.method == "POST":
        evidence_id = request.form.get("evidence_id", type=int)
        assignee = request.form.get("assignee_username", "").strip().lower()
        role = request.form.get("assignee_role", "Investigator")
        if evidence_id and assignee and assignee in assignable_emails:
            with SessionLocal() as db:
                db.merge(
                    CaseAssignment(
                        evidence_id=evidence_id,
                        assignee_username=assignee,
                        assigner_username=session["user"],
                        assignee_role=role,
                    )
                )
                db.commit()
            flash("Assignment saved.", "success")
        else:
            flash("Evidence ID and valid assignee email are required.", "danger")
        return redirect(url_for("admin.admin_assign_cases"))
    return render_template(
        "admin_assign.html",
        cases=cases,
        users=users_dict(),
        assignments=assignments,
    )


@admin_bp.route("/admin/requests", methods=["GET", "POST"])
@admin_required
def admin_case_requests():
    if request.method == "POST":
        req_id = request.form.get("request_id", type=int)
        action = request.form.get("action")
        with SessionLocal() as db:
            r = db.get(CaseAccessRequest, req_id)
            if r and action == "approve":
                r.status = "approved"
                r.decided_by = session["user"]
                r.decided_at = utcnow()
            elif r and action == "reject":
                r.status = "rejected"
                r.decided_by = session["user"]
                r.decided_at = utcnow()
            db.commit()
        return redirect(url_for("admin.admin_case_requests"))
    with SessionLocal() as db:
        reqs = db.scalars(
            select(CaseAccessRequest).order_by(CaseAccessRequest.created_at.desc())
        ).all()
    return render_template("admin_requests.html", requests=reqs)

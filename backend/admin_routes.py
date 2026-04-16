"""Admin-only routes: user management, case assignment, case access requests."""

from __ __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func, select

from auth import admin_required
from database import (
    CaseAccessRequest,
    CaseAssignment,
    ForensicCase,
    SessionLocal,
    utcnow,
)
from users_config import USERS

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def admin_home():
    return render_template("admin_home.html", users=USERS)


@admin_bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "Member")
        if username and password and name and role in ("Admin", "Investigator", "Member"):
            if username in USERS:
                flash("User already exists.", "warning")
            else:
                USERS[username] = {
                    "password": password,
                    "role": role,
                    "name": name,
                }
                flash(f"User {username} added with role {role}.", "success")
        else:
            flash("All fields required.", "danger")
    return render_template("admin_users.html", users=USERS)


@admin_bp.route("/admin/cases/assign", methods=["GET", "POST"])
@admin_required
def admin_assign_cases():
    with SessionLocal() as db:
        cases = db.scalars(select(ForensicCase).order_by(ForensicCase.id.desc())).all()
        users = [u for u, d in USERS.items() if d.get("role") in ("Investigator", "Member")]
    if request.method == "POST":
        evidence_id = request.form.get("evidence_id", type=int)
        assignee = request.form.get("assignee_username", "").strip()
        role = request.form.get("assignee_role", "Investigator")
        if evidence_id and assignee and assignee in USERS:
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
        return redirect(url_for("admin.admin_assign_cases"))
    return render_template("admin_assign.html", cases=cases, users=users)


@admin_bp.route("/admin/requests")
@admin_required
def admin_case_requests():
    with SessionLocal() as db:
        reqs = db.scalars(
            select(CaseAccessRequest).order_by(CaseAccessRequest.created_at.desc())
        ).all()
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
                r.decided_by = session[" User"]
                r.decided_at = utcnow()
            db.commit()
        return redirect(url_for("admin.admin_case_requests"))
    return render_template("admin_requests.html", requests=reqs)

"""Cases, transfer approvals, alerts, reports, time locks."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func, select

from auth import (
    can_access_evidence,
    can_mutate_chain_custody,
    login_required,
    role_required,
)
from blockchain_utils import (
    ACTION_CODES,
    blockchain_status,
    contract,
    format_event,
    get_ganache_account,
    w3,
)
from custody_services import log_audit
from database import (
    CaseEvidenceLink,
    EvidenceTimeLock,
    ForensicCase,
    SecurityAlert,
    SessionLocal,
    TransferRequest,
    utcnow,
)
from users_config import all_usernames, users_dict

features_bp = Blueprint("features", __name__)


@features_bp.route("/cases")
@login_required
def cases_list():
    with SessionLocal() as db:
        cases = db.scalars(
            select(ForensicCase).order_by(ForensicCase.created_at.desc())
        ).all()
    return render_template("cases_list.html", cases=cases)


@features_bp.route("/cases/new", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Investigator")
def cases_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip() or None
        if not title:
            flash("Title is required.", "danger")
            return redirect(request.url)
        with SessionLocal() as db:
            n = db.scalar(select(func.count()).select_from(ForensicCase)) or 0
            case_number = f"FYP-{n + 1:05d}"
            c = ForensicCase(
                case_number=case_number,
                title=title,
                description=description,
                created_by=session["user"],
            )
            db.add(c)
            db.flush()
            cid = c.id
            db.commit()
        flash(f"Case {case_number} created.", "success")
        return redirect(url_for("features.case_detail", case_id=cid))
    return render_template("cases_new.html")


@features_bp.route("/cases/<int:case_id>")
@login_required
def case_detail(case_id):
    with SessionLocal() as db:
        case = db.get(ForensicCase, case_id)
        if case is None:
            flash("Case not found.", "danger")
            return redirect(url_for("features.cases_list"))
        links = db.scalars(
            select(CaseEvidenceLink)
            .where(CaseEvidenceLink.case_id == case_id)
            .order_by(CaseEvidenceLink.added_at.desc())
        ).all()
    ev_rows = []
    st = blockchain_status()
    if st["deployed"] and st["connected"]:
        for link in links:
            try:
                raw = contract.functions.getEvidence(link.evidence_id).call()
                ev_rows.append(
                    {
                        "evidence_id": link.evidence_id,
                        "fileName": raw[2],
                        "fileHash": raw[1],
                        "uploadedBy": raw[5],
                    }
                )
            except Exception:
                ev_rows.append({"evidence_id": link.evidence_id, "fileName": "?", "fileHash": "", "uploadedBy": "?"})
    return render_template(
        "case_detail.html",
        case=case,
        links=links,
        ev_rows=ev_rows,
        users=all_usernames(),
    )


@features_bp.route("/cases/<int:case_id>/link", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def case_link_evidence(case_id):
    evidence_id = request.form.get("evidence_id", type=int)
    if not evidence_id:
        flash("Evidence ID required.", "danger")
        return redirect(url_for("features.case_detail", case_id=case_id))
    with SessionLocal() as db:
        case = db.get(ForensicCase, case_id)
        if case is None:
            flash("Case not found.", "danger")
            return redirect(url_for("features.cases_list"))
        exists = db.scalar(
            select(func.count())
            .select_from(CaseEvidenceLink)
            .where(
                CaseEvidenceLink.case_id == case_id,
                CaseEvidenceLink.evidence_id == evidence_id,
            )
        )
        if exists:
            flash("Evidence already linked to this case.", "warning")
            return redirect(url_for("features.case_detail", case_id=case_id))
        db.add(CaseEvidenceLink(case_id=case_id, evidence_id=evidence_id))
        log_audit(
            db,
            username=session["user"],
            action="case_link",
            detail=f"Linked evidence #{evidence_id} to case {case.case_number}",
            evidence_id=evidence_id,
            case_id=case_id,
        )
        db.commit()
    flash(f"Evidence #{evidence_id} linked to case.", "success")
    return redirect(url_for("features.case_detail", case_id=case_id))


@features_bp.route("/cases/<int:case_id>/report")
@login_required
@role_required("Admin", "Investigator")
def case_report(case_id):
    with SessionLocal() as db:
        case = db.get(ForensicCase, case_id)
        if case is None:
            flash("Case not found.", "danger")
            return redirect(url_for("features.cases_list"))
        links = db.scalars(
            select(CaseEvidenceLink).where(CaseEvidenceLink.case_id == case_id)
        ).all()
    items = []
    st = blockchain_status()
    for link in links:
        row = {"evidence_id": link.evidence_id, "meta": None, "chain_len": 0}
        if st["deployed"] and st["connected"]:
            try:
                raw = contract.functions.getEvidence(link.evidence_id).call()
                row["meta"] = {
                    "fileName": raw[2],
                    "fileHash": raw[1],
                    "uploadedBy": raw[5],
                }
                ch = contract.functions.getCustodyChain(link.evidence_id).call()
                row["chain_len"] = len(ch)
            except Exception:
                pass
        items.append(row)
    return render_template(
        "report_case.html",
        case=case,
        items=items,
        generated_at=utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    )


@features_bp.route("/transfers")
@login_required
def transfers_inbox():
    with SessionLocal() as db:
        if session.get("role") == "Admin":
            rows = db.scalars(
                select(TransferRequest).order_by(TransferRequest.created_at.desc())
            ).all()
        else:
            u = session["user"]
            rows = db.scalars(
                select(TransferRequest)
                .where(
                    (TransferRequest.to_username == u)
                    | (TransferRequest.from_username == u)
                )
                .order_by(TransferRequest.created_at.desc())
            ).all()
    return render_template("transfers.html", transfers=rows, users_map=users_dict())


@features_bp.route("/transfers/<int:tid>/approve", methods=["POST"])
@login_required
def transfer_approve(tid):
    if not can_mutate_chain_custody(session.get("role")):
        flash("Only Admin or Investigator may approve custody transfers.", "danger")
        return redirect(url_for("features.transfers_inbox"))
    with SessionLocal() as db:
        tr = db.get(TransferRequest, tid)
        if tr is None or tr.status != "pending":
            flash("Invalid transfer request.", "danger")
            return redirect(url_for("features.transfers_inbox"))
        if session["user"] != tr.to_username and session.get("role") != "Admin":
            flash("Only the recipient (or Admin) can approve.", "danger")
            return redirect(url_for("features.transfers_inbox"))
        if not blockchain_status()["deployed"]:
            flash("Blockchain not available.", "danger")
            return redirect(url_for("features.transfers_inbox"))
        try:
            ev = contract.functions.getEvidence(tr.evidence_id).call()
            acct = get_ganache_account()
            notes = (
                f"Approved custody transfer from {tr.from_username} to {tr.to_username}. "
                f"{tr.notes or ''}"
            )
            tx = contract.functions.logCustodyEvent(
                tr.evidence_id,
                ev[1],
                ACTION_CODES["Transferred"],
                str(session.get("user_id", "")),
                notes,
            ).transact({"from": acct, "gas": 1_500_000})
            w3.eth.wait_for_transaction_receipt(tx)
            tr.status = "approved"
            tr.decided_at = utcnow()
            tr.decided_by = session["user"]
            log_audit(
                db,
                username=session["user"],
                action="transfer_approved",
                detail=f"Request #{tid} evidence #{tr.evidence_id}",
                evidence_id=tr.evidence_id,
            )
            db.commit()
            flash("Transfer approved and recorded on-chain.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Blockchain error: {e}", "danger")
    return redirect(url_for("features.transfers_inbox"))


@features_bp.route("/transfers/<int:tid>/reject", methods=["POST"])
@login_required
def transfer_reject(tid):
    if not can_mutate_chain_custody(session.get("role")):
        flash("Only Admin or Investigator may reject custody transfers.", "danger")
        return redirect(url_for("features.transfers_inbox"))
    with SessionLocal() as db:
        tr = db.get(TransferRequest, tid)
        if tr is None or tr.status != "pending":
            flash("Invalid transfer request.", "danger")
            return redirect(url_for("features.transfers_inbox"))
        if session["user"] != tr.to_username and session.get("role") != "Admin":
            flash("Only the recipient (or Admin) can reject.", "danger")
            return redirect(url_for("features.transfers_inbox"))
        tr.status = "rejected"
        tr.decided_at = utcnow()
        tr.decided_by = session["user"]
        log_audit(
            db,
            username=session["user"],
            action="transfer_rejected",
            detail=f"Request #{tid}",
            evidence_id=tr.evidence_id,
        )
        db.commit()
    flash("Transfer request rejected.", "info")
    return redirect(url_for("features.transfers_inbox"))


@features_bp.route("/evidence/<int:evidence_id>/transfer-request", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def request_transfer(evidence_id):
    if not can_access_evidence(session["user"], evidence_id):
        flash("You do not have access to this evidence.", "danger")
        return redirect(url_for("evidence_list"))
    to_u = request.form.get("to_username", "").strip().lower()
    notes = request.form.get("notes", "").strip() or None
    if to_u not in users_dict():
        flash("Invalid recipient user.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))
    if to_u == session["user"]:
        flash("Choose a different user than yourself.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))
    with SessionLocal() as db:
        db.add(
            TransferRequest(
                evidence_id=evidence_id,
                from_username=session["user"],
                to_username=to_u,
                status="pending",
                notes=notes,
            )
        )
        log_audit(
            db,
            username=session["user"],
            action="transfer_request",
            detail=f"To {to_u}",
            evidence_id=evidence_id,
        )
        db.commit()
    flash("Transfer request sent — recipient must approve under Transfers.", "success")
    return redirect(url_for("evidence_detail", evidence_id=evidence_id))


@features_bp.route("/evidence/<int:evidence_id>/time-lock", methods=["POST"])
@login_required
@role_required("Admin")
def set_evidence_time_lock(evidence_id):
    raw = request.form.get("unlock_at", "").strip()
    if not raw:
        flash("Unlock time required.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        flash("Invalid date/time.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))
    with SessionLocal() as db:
        db.merge(
            EvidenceTimeLock(
                evidence_id=evidence_id,
                unlock_at=dt,
                set_by=session["user"],
            )
        )
        log_audit(
            db,
            username=session["user"],
            action="time_lock_set",
            detail=f"Unlock at {dt.isoformat()}",
            evidence_id=evidence_id,
        )
        db.commit()
    flash("Time lock updated.", "success")
    return redirect(url_for("evidence_detail", evidence_id=evidence_id))


@features_bp.route("/alerts")
@login_required
def alerts_list():
    with SessionLocal() as db:
        rows = db.scalars(
            select(SecurityAlert).order_by(SecurityAlert.created_at.desc()).limit(200)
        ).all()
    return render_template("alerts.html", alerts=rows)


@features_bp.route("/alerts/<int:aid>/ack", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def alert_ack(aid):
    with SessionLocal() as db:
        a = db.get(SecurityAlert, aid)
        if a:
            a.acknowledged = True
            db.commit()
    return redirect(url_for("features.alerts_list"))


@features_bp.route("/evidence/<int:evidence_id>/timeline")
@login_required
def evidence_timeline(evidence_id):
    if not can_access_evidence(session["user"], evidence_id):
        flash("You do not have access to this evidence.", "danger")
        return redirect(url_for("evidence_list"))
    status = blockchain_status()
    chain = []
    ev_data = None
    if status["deployed"] and status["connected"]:
        try:
            raw = contract.functions.getEvidence(evidence_id).call()
            ev_data = {
                "id": raw[0],
                "fileName": raw[2],
                "uploadedBy": raw[5],
            }
            raw_chain = contract.functions.getCustodyChain(evidence_id).call()
            chain = [format_event(e) for e in raw_chain]
        except Exception as e:
            flash(str(e), "danger")
    return render_template(
        "evidence_timeline.html",
        evidence=ev_data,
        chain=chain,
        evidence_id=evidence_id,
    )

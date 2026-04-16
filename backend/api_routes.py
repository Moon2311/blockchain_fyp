"""JSON REST API for the React SPA (session cookie auth, credentials via Vite proxy)."""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import func, select
from werkzeug.utils import secure_filename

from auth import (
    admin_required,
    can_access_evidence,
    can_mutate_chain_custody,
    login_required,
    login_user,
    register_user,
    role_required,
)
from blockchain_utils import (
    ACTION_CODES,
    ACTION_NAMES,
    blockchain_status,
    contract,
    format_event,
    get_ganache_account,
    w3,
)
from custody_services import (
    add_security_alert,
    compute_integrity_score,
    detect_suspicious_activity,
    is_evidence_locked,
    log_audit,
    record_verification,
    role_can_log_action,
    sign_action_hmac,
    try_ipfs_add_file,
    validate_custody_chain,
)
from database import (
    AuditLogEntry,
    CaseAccessRequest,
    CaseAssignment,
    CaseEvidenceLink,
    EvidenceTimeLock,
    ForensicCase,
    HelpTopic,
    OffChainEvidenceMeta,
    SecurityAlert,
    SessionLocal,
    TransferRequest,
    User,
    VerificationRecord,
    utcnow,
)
from media_config import ALLOWED_EXTENSIONS, allowed_file, fernet, sha256_bytes, UPLOAD_DIR
from users_config import all_usernames, users_dict

api_bp = Blueprint("api", __name__, url_prefix="/api")

EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def _parse_optional_float(data, key):
    v = (data.get(key) or "").strip() if isinstance(data.get(key), str) else data.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _dt_iso(dt):
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _alert_json(a):
    return {
        "id": a.id,
        "level": a.level,
        "code": a.code,
        "message": a.message,
        "evidence_id": a.evidence_id,
        "acknowledged": a.acknowledged,
        "created_at": _dt_iso(a.created_at),
    }


def _transfer_json(t):
    return {
        "id": t.id,
        "evidence_id": t.evidence_id,
        "from_username": t.from_username,
        "to_username": t.to_username,
        "status": t.status,
        "notes": t.notes,
        "created_at": _dt_iso(t.created_at),
        "decided_at": _dt_iso(t.decided_at),
        "decided_by": t.decided_by,
    }


def _case_json(c):
    return {
        "id": c.id,
        "case_number": c.case_number,
        "title": c.title,
        "description": c.description,
        "created_by": c.created_by,
        "created_at": _dt_iso(c.created_at),
    }


def _offchain_json(o):
    if o is None:
        return None
    return {
        "evidence_id": o.evidence_id,
        "relative_filename": o.relative_filename,
        "ipfs_cid": o.ipfs_cid,
        "storage_mode": o.storage_mode,
        "created_at": _dt_iso(o.created_at),
    }


def _onchain_actor_label(actor: str) -> str:
    """Map numeric on-chain actor / uploader id to a readable label; pass through legacy strings."""
    s = (actor or "").strip()
    if not s.isdigit():
        return s
    uid = int(s)
    with SessionLocal() as db:
        u = db.get(User, uid)
        if u:
            return f"{u.name} ({u.email}, id {uid})"
    return s


# ── Public / auth ─────────────────────────────────────────────────────────────


@api_bp.route("/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    u = login_user(email, password)
    if not u:
        return jsonify({"error": "Invalid email or password."}), 401
    session["user"] = u.email
    session["user_id"] = u.id
    session["role"] = u.role
    session["name"] = u.name
    session.permanent = True
    with SessionLocal() as db:
        log_audit(db, username=u.email, action="login", detail=None)
        db.commit()
    return jsonify(
        {
            "user": {"email": u.email, "name": u.name, "role": u.role, "id": u.id},
        }
    )


@api_bp.route("/auth/logout", methods=["POST"])
def api_auth_logout():
    session.clear()
    return jsonify({"ok": True})


@api_bp.route("/auth/me", methods=["GET"])
def api_auth_me():
    if "user" not in session:
        return jsonify({"user": None}), 200
    return jsonify(
        {
            "user": {
                "email": session["user"],
                "name": session.get("name"),
                "role": session.get("role"),
                "id": session.get("user_id"),
            }
        }
    )


@api_bp.route("/auth/register", methods=["POST"])
def api_auth_register():
    if "user" in session:
        return jsonify({"error": "Already logged in."}), 400
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    password2 = data.get("password2") or ""
    name = (data.get("name") or "").strip()
    role = data.get("role", "Viewer")
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Enter a valid email address."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if password != password2:
        return jsonify({"error": "Passwords do not match."}), 400
    if not name:
        return jsonify({"error": "Name is required."}), 400
    if role not in ("Investigator", "Viewer", "Member"):
        return jsonify({"error": "Choose Investigator or Viewer."}), 400
    try:
        register_user(email, password, name, role)
        with SessionLocal() as db:
            log_audit(
                db,
                username=email,
                action="user_register",
                detail=f"role={role}",
            )
            db.commit()
        return jsonify({"ok": True, "message": "Account created."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── Status & nav ──────────────────────────────────────────────────────────────


@api_bp.route("/status")
def api_status():
    return jsonify(blockchain_status())


@api_bp.route("/nav-counts", methods=["GET"])
@login_required
def api_nav_counts():
    with SessionLocal() as db:
        q = select(func.count()).select_from(TransferRequest).where(
            TransferRequest.status == "pending"
        )
        if session.get("role") != "Admin":
            q = q.where(TransferRequest.to_username == session["user"])
        pending = db.scalar(q) or 0
        unack = db.scalar(
            select(func.count())
            .select_from(SecurityAlert)
            .where(SecurityAlert.acknowledged.is_(False))
        ) or 0
    return jsonify({"pending_transfers": pending, "alerts_unack": unack})


@api_bp.route("/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    status = blockchain_status()
    stats = {"total": 0, "recent": []}
    if status["deployed"] and status["connected"]:
        try:
            count = contract.functions.getEvidenceCount().call()
            stats["total"] = count
            recent = []
            for eid in range(max(1, count - 4), count + 1):
                ev = contract.functions.getEvidence(eid).call()
                recent.append(
                    {
                        "id": ev[0],
                        "fileName": ev[2],
                        "fileType": ev[3],
                        "uploadedBy": ev[5],
                        "createdAt": time.strftime(
                            "%Y-%m-%d %H:%M", time.localtime(ev[6])
                        ),
                        "encrypted": ev[8],
                        "events": ev[9],
                    }
                )
            stats["recent"] = list(reversed(recent))
        except Exception as e:
            stats["error"] = str(e)
    with SessionLocal() as db:
        recent_alerts = db.scalars(
            select(SecurityAlert)
            .order_by(SecurityAlert.created_at.desc())
            .limit(8)
        ).all()
    return jsonify(
        {
            "blockchain": status,
            "stats": stats,
            "recent_alerts": [_alert_json(a) for a in recent_alerts],
        }
    )


# ── Upload ────────────────────────────────────────────────────────────────────


@api_bp.route("/upload/options", methods=["GET"])
@login_required
@role_required("Admin", "Investigator")
def api_upload_options():
    next_id = 1
    if blockchain_status()["deployed"] and blockchain_status()["connected"]:
        try:
            next_id = contract.functions.getEvidenceCount().call() + 1
        except Exception:
            pass
    with SessionLocal() as db:
        cases = db.scalars(
            select(ForensicCase).order_by(ForensicCase.id.desc())
        ).all()
    return jsonify(
        {
            "next_id": next_id,
            "cases": [_case_json(c) for c in cases],
            "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        }
    )


@api_bp.route("/upload", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file selected."}), 400
    file = request.files["file"]
    encrypt = request.form.get("encrypt") in ("on", "true", "1")
    uploader_on_chain = str(session.get("user_id", ""))
    notes = request.form.get(
        "notes", "Evidence collected and recorded on blockchain"
    )
    case_id = request.form.get("case_id", type=int)
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed."}), 400
    filename = secure_filename(file.filename)
    raw_bytes = file.read()
    file_hash = sha256_bytes(raw_bytes)
    stored_bytes = fernet.encrypt(raw_bytes) if encrypt else raw_bytes
    save_name = ("enc_" + filename) if encrypt else filename
    save_path = os.path.join(UPLOAD_DIR, save_name)
    with open(save_path, "wb") as f:
        f.write(stored_bytes)
    if not blockchain_status()["deployed"]:
        return jsonify({"error": "Blockchain not deployed. Run deploy.py first."}), 400
    try:
        account = get_ganache_account()
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        tx_hash = contract.functions.addEvidence(
            file_hash,
            filename,
            ext,
            len(raw_bytes),
            uploader_on_chain,
            encrypt,
        ).transact({"from": account, "gas": 3_000_000})
        w3.eth.wait_for_transaction_receipt(tx_hash)
        ev_id = contract.functions.getEvidenceCount().call()
        ipfs_cid = try_ipfs_add_file(save_path)
        with SessionLocal() as db:
            db.merge(
                OffChainEvidenceMeta(
                    evidence_id=ev_id,
                    relative_filename=save_name,
                    ipfs_cid=ipfs_cid,
                    storage_mode="hybrid" if ipfs_cid else "local",
                )
            )
            if case_id:
                case = db.get(ForensicCase, case_id)
                if case:
                    exists = db.scalar(
                        select(func.count())
                        .select_from(CaseEvidenceLink)
                        .where(
                            CaseEvidenceLink.case_id == case_id,
                            CaseEvidenceLink.evidence_id == ev_id,
                        )
                    )
                    if not exists:
                        db.add(
                            CaseEvidenceLink(case_id=case_id, evidence_id=ev_id)
                        )
            log_audit(
                db,
                username=session["user"],
                action="evidence_register",
                detail=notes[:500] if notes else None,
                evidence_id=ev_id,
                case_id=case_id if case_id else None,
            )
            db.commit()
        return jsonify(
            {
                "evidence_id": ev_id,
                "file_hash_prefix": file_hash[:20],
                "message": "Evidence recorded on blockchain.",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Evidence ──────────────────────────────────────────────────────────────────


def _evidence_list_items():
    items = []
    status = blockchain_status()
    if status["deployed"] and status["connected"]:
        try:
            count = contract.functions.getEvidenceCount().call()
            for eid in range(1, count + 1):
                ev = contract.functions.getEvidence(eid).call()
                items.append(
                    {
                        "id": ev[0],
                        "fileHash": ev[1],
                        "fileName": ev[2],
                        "fileType": ev[3],
                        "fileSize": ev[4],
                        "uploadedBy": ev[5],
                        "createdAt": time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(ev[6])
                        ),
                        "encrypted": ev[8],
                        "events": ev[9],
                    }
                )
            items = list(reversed(items))
        except Exception as e:
            return None, status, str(e)
    role = session.get("role")
    user_email = session.get("user")
    if role in ("Investigator", "Member", "Viewer") and user_email:
        with SessionLocal() as db:
            allowed = set(
                db.scalars(
                    select(CaseAssignment.evidence_id).where(
                        CaseAssignment.assignee_username == user_email
                    )
                ).all()
            )
        items = [x for x in items if x["id"] in allowed]
    return items, status, None


@api_bp.route("/evidence", methods=["GET"])
@login_required
def api_evidence_list():
    items, status, err = _evidence_list_items()
    if err:
        return jsonify({"blockchain": status, "items": [], "warning": err})
    return jsonify({"blockchain": status, "items": items})


@api_bp.route("/evidence/<int:evidence_id>", methods=["GET"])
@login_required
def api_evidence_detail(evidence_id):
    if not can_access_evidence(session["user"], evidence_id):
        return jsonify({"error": "forbidden"}), 403
    status = blockchain_status()
    ev_data, chain = None, []
    offchain = None
    integrity_score = None
    validation_ok, validation_issues = True, []
    suspicious_flags = []
    locked_view = False
    unlock_at = None
    err = None
    if status["deployed"] and status["connected"]:
        try:
            raw = contract.functions.getEvidence(evidence_id).call()
            ub = str(raw[5])
            ev_data = {
                "id": raw[0],
                "fileHash": raw[1],
                "fileName": raw[2],
                "fileType": raw[3],
                "fileSize": raw[4],
                "uploadedBy": ub,
                "uploadedByLabel": _onchain_actor_label(ub),
                "createdAt": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(raw[6])
                ),
                "encrypted": raw[8],
                "events": raw[9],
            }
            raw_chain = contract.functions.getCustodyChain(evidence_id).call()
            chain = [format_event(e) for e in raw_chain]
            for c in chain:
                c["actor_label"] = _onchain_actor_label(str(c.get("actor", "")))
            validation_ok, validation_issues = validate_custody_chain(chain)
            with SessionLocal() as db:
                integrity_score = compute_integrity_score(db, evidence_id, chain)
            suspicious_flags = detect_suspicious_activity(evidence_id)
        except Exception as e:
            err = str(e)
    with SessionLocal() as db:
        offchain = db.get(OffChainEvidenceMeta, evidence_id)
    locked, unlock_at = is_evidence_locked(evidence_id)
    if locked and session.get("role") != "Admin":
        locked_view = True
    users_for_transfer = [u for u in all_usernames() if u != session["user"]]
    can_manage = can_mutate_chain_custody(session.get("role"))
    return jsonify(
        {
            "blockchain": status,
            "evidence": ev_data,
            "chain": chain,
            "action_names": ACTION_NAMES if can_manage else {},
            "offchain": _offchain_json(offchain),
            "integrity_score": integrity_score,
            "validation_ok": validation_ok,
            "validation_issues": validation_issues,
            "suspicious_flags": suspicious_flags,
            "locked_view": locked_view,
            "unlock_at": _dt_iso(unlock_at) if unlock_at else None,
            "users_for_transfer": users_for_transfer if can_manage else [],
            "can_manage_custody": can_manage,
            "error": err,
        }
    )


@api_bp.route("/evidence/<int:evidence_id>/chain", methods=["GET"])
@login_required
def api_evidence_chain(evidence_id):
    if not can_access_evidence(session["user"], evidence_id):
        return jsonify({"error": "forbidden"}), 403
    try:
        raw = contract.functions.getCustodyChain(evidence_id).call()
        return jsonify([format_event(e) for e in raw])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/evidence/<int:evidence_id>/action", methods=["POST"])
@login_required
def api_log_action(evidence_id):
    if not can_access_evidence(session["user"], evidence_id):
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    action_name = data.get("action")
    notes = data.get("notes") or ""
    geo_lat = _parse_optional_float(data, "geo_lat")
    geo_lng = _parse_optional_float(data, "geo_lng")
    locked, _ = is_evidence_locked(evidence_id)
    if locked and session.get("role") != "Admin":
        return jsonify({"error": "Time-locked; only Admin may act."}), 403
    if action_name not in ACTION_CODES:
        return jsonify({"error": "Invalid action."}), 400
    if not role_can_log_action(session.get("role"), action_name):
        return jsonify({"error": "Role cannot perform this action."}), 403
    try:
        ev = contract.functions.getEvidence(evidence_id).call()
        acct = get_ganache_account()
        tx = contract.functions.logCustodyEvent(
            evidence_id,
            ev[1],
            ACTION_CODES[action_name],
            str(session.get("user_id", "")),
            notes,
        ).transact({"from": acct, "gas": 1_000_000})
        w3.eth.wait_for_transaction_receipt(tx)
        sig = sign_action_hmac(
            current_app.secret_key,
            session["user"],
            evidence_id,
            action_name,
            notes,
        )
        with SessionLocal() as db:
            log_audit(
                db,
                username=session["user"],
                action="chain_action",
                detail=f"{action_name}: {notes}"[:2000],
                evidence_id=evidence_id,
                geo_lat=geo_lat,
                geo_lng=geo_lng,
                signature_hex=sig,
            )
            db.commit()
        return jsonify({"ok": True, "message": f"Action '{action_name}' recorded."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/verify", methods=["GET"])
@login_required
def api_verify_get():
    count = 0
    if blockchain_status()["deployed"]:
        try:
            count = contract.functions.getEvidenceCount().call()
        except Exception:
            pass
    return jsonify({"evidence_count": count})


@api_bp.route("/verify", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def api_verify_post():
    evidence_id = request.form.get("evidence_id", type=int)
    file = request.files.get("file")
    geo_lat = _parse_optional_float(request.form, "geo_lat")
    geo_lng = _parse_optional_float(request.form, "geo_lng")
    if evidence_id is None or not can_access_evidence(session["user"], evidence_id):
        return jsonify({"error": "Invalid evidence or access denied."}), 403
    if not file or file.filename == "":
        return jsonify({"error": "Please upload a file."}), 400
    raw_bytes = file.read()
    new_hash = sha256_bytes(raw_bytes)
    try:
        authentic, stored_hash = contract.functions.verifyEvidence(
            evidence_id, new_hash
        ).call()
        ev = contract.functions.getEvidence(evidence_id).call()
        with SessionLocal() as db:
            record_verification(db, evidence_id, authentic, session["user"])
            log_audit(
                db,
                username=session["user"],
                action="verify_attempt",
                detail=f"authentic={authentic}",
                evidence_id=evidence_id,
                geo_lat=geo_lat,
                geo_lng=geo_lng,
            )
            if authentic:
                acct = get_ganache_account()
                vtx = contract.functions.logCustodyEvent(
                    evidence_id,
                    new_hash,
                    ACTION_CODES["Verified"],
                    str(session.get("user_id", "")),
                    "Integrity verification performed — hash match",
                ).transact({"from": acct, "gas": 1_000_000})
                w3.eth.wait_for_transaction_receipt(vtx)
            else:
                add_security_alert(
                    db,
                    level="danger",
                    code="TAMPER_DETECTED",
                    message=f"Hash mismatch for evidence #{evidence_id}. Possible tampering.",
                    evidence_id=evidence_id,
                )
            db.commit()
        return jsonify(
            {
                "authentic": authentic,
                "evidence_id": evidence_id,
                "file_name": ev[2],
                "new_hash": new_hash,
                "stored_hash": stored_hash,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Cases & features ──────────────────────────────────────────────────────────


@api_bp.route("/cases", methods=["GET"])
@login_required
def api_cases_list():
    with SessionLocal() as db:
        cases = db.scalars(
            select(ForensicCase).order_by(ForensicCase.created_at.desc())
        ).all()
    return jsonify({"cases": [_case_json(c) for c in cases]})


@api_bp.route("/cases", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def api_cases_new():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip() or None
    if not title:
        return jsonify({"error": "Title is required."}), 400
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
        cn = c.case_number
        payload = _case_json(c)
        db.commit()
    return jsonify({"case": payload, "case_number": cn})


@api_bp.route("/cases/<int:case_id>", methods=["GET"])
@login_required
def api_case_detail(case_id):
    with SessionLocal() as db:
        case = db.get(ForensicCase, case_id)
        if case is None:
            return jsonify({"error": "not found"}), 404
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
                ev_rows.append(
                    {
                        "evidence_id": link.evidence_id,
                        "fileName": "?",
                        "fileHash": "",
                        "uploadedBy": "?",
                    }
                )
    return jsonify(
        {
            "case": _case_json(case),
            "links": [{"evidence_id": l.evidence_id, "added_at": _dt_iso(l.added_at)} for l in links],
            "ev_rows": ev_rows,
            "users": all_usernames(),
        }
    )


@api_bp.route("/cases/<int:case_id>/link", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def api_case_link(case_id):
    data = request.get_json(silent=True) or {}
    raw_eid = data.get("evidence_id")
    evidence_id = None
    try:
        if raw_eid is not None:
            evidence_id = int(raw_eid)
    except (TypeError, ValueError):
        evidence_id = None
    if not evidence_id:
        return jsonify({"error": "Evidence ID required."}), 400
    with SessionLocal() as db:
        case = db.get(ForensicCase, case_id)
        if case is None:
            return jsonify({"error": "Case not found."}), 404
        exists = db.scalar(
            select(func.count())
            .select_from(CaseEvidenceLink)
            .where(
                CaseEvidenceLink.case_id == case_id,
                CaseEvidenceLink.evidence_id == evidence_id,
            )
        )
        if exists:
            return jsonify({"error": "Already linked."}), 400
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
    return jsonify({"ok": True})


@api_bp.route("/cases/<int:case_id>/report", methods=["GET"])
@login_required
@role_required("Admin", "Investigator")
def api_case_report(case_id):
    with SessionLocal() as db:
        case = db.get(ForensicCase, case_id)
        if case is None:
            return jsonify({"error": "not found"}), 404
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
    return jsonify(
        {
            "case": _case_json(case),
            "items": items,
            "generated_at": utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
    )


@api_bp.route("/transfers", methods=["GET"])
@login_required
def api_transfers():
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
    return jsonify(
        {"transfers": [_transfer_json(t) for t in rows], "users_map": users_dict()}
    )


@api_bp.route("/transfers/<int:tid>/approve", methods=["POST"])
@login_required
def api_transfer_approve(tid):
    if not can_mutate_chain_custody(session.get("role")):
        return jsonify({"error": "Forbidden."}), 403
    with SessionLocal() as db:
        tr = db.get(TransferRequest, tid)
        if tr is None or tr.status != "pending":
            return jsonify({"error": "Invalid transfer request."}), 400
        if session["user"] != tr.to_username and session.get("role") != "Admin":
            return jsonify({"error": "Forbidden."}), 403
        if not blockchain_status()["deployed"]:
            return jsonify({"error": "Blockchain not available."}), 400
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
            return jsonify({"ok": True})
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500


@api_bp.route("/transfers/<int:tid>/reject", methods=["POST"])
@login_required
def api_transfer_reject(tid):
    if not can_mutate_chain_custody(session.get("role")):
        return jsonify({"error": "Forbidden."}), 403
    with SessionLocal() as db:
        tr = db.get(TransferRequest, tid)
        if tr is None or tr.status != "pending":
            return jsonify({"error": "Invalid transfer request."}), 400
        if session["user"] != tr.to_username and session.get("role") != "Admin":
            return jsonify({"error": "Forbidden."}), 403
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
    return jsonify({"ok": True})


@api_bp.route("/evidence/<int:evidence_id>/transfer-request", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def api_request_transfer(evidence_id):
    if not can_access_evidence(session["user"], evidence_id):
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    to_u = (data.get("to_username") or "").strip().lower()
    notes = (data.get("notes") or "").strip() or None
    if to_u not in users_dict():
        return jsonify({"error": "Invalid recipient."}), 400
    if to_u == session["user"]:
        return jsonify({"error": "Choose another user."}), 400
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
    return jsonify({"ok": True})


@api_bp.route("/evidence/<int:evidence_id>/time-lock", methods=["POST"])
@login_required
@role_required("Admin")
def api_time_lock(evidence_id):
    data = request.get_json(silent=True) or {}
    raw = (data.get("unlock_at") or "").strip()
    if not raw:
        return jsonify({"error": "Unlock time required."}), 400
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return jsonify({"error": "Invalid date/time."}), 400
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
    return jsonify({"ok": True})


@api_bp.route("/alerts", methods=["GET"])
@login_required
def api_alerts():
    with SessionLocal() as db:
        rows = db.scalars(
            select(SecurityAlert).order_by(SecurityAlert.created_at.desc()).limit(200)
        ).all()
    return jsonify({"alerts": [_alert_json(a) for a in rows]})


@api_bp.route("/alerts/<int:aid>/ack", methods=["POST"])
@login_required
@role_required("Admin", "Investigator")
def api_alert_ack(aid):
    with SessionLocal() as db:
        a = db.get(SecurityAlert, aid)
        if a:
            a.acknowledged = True
            db.commit()
    return jsonify({"ok": True})


@api_bp.route("/evidence/<int:evidence_id>/timeline", methods=["GET"])
@login_required
def api_evidence_timeline(evidence_id):
    if not can_access_evidence(session["user"], evidence_id):
        return jsonify({"error": "forbidden"}), 403
    status = blockchain_status()
    chain = []
    ev_data = None
    err = None
    if status["deployed"] and status["connected"]:
        try:
            raw = contract.functions.getEvidence(evidence_id).call()
            ub = str(raw[5])
            ev_data = {
                "id": raw[0],
                "fileName": raw[2],
                "uploadedBy": ub,
                "uploadedByLabel": _onchain_actor_label(ub),
            }
            raw_chain = contract.functions.getCustodyChain(evidence_id).call()
            chain = [format_event(e) for e in raw_chain]
            for c in chain:
                c["actor_label"] = _onchain_actor_label(str(c.get("actor", "")))
        except Exception as e:
            err = str(e)
    return jsonify({"evidence": ev_data, "chain": chain, "error": err})


# ── Help ─────────────────────────────────────────────────────────────────────


@api_bp.route("/help/topics", methods=["GET"])
@login_required
def api_help_topics():
    with SessionLocal() as db:
        rows = db.scalars(select(HelpTopic).order_by(HelpTopic.id)).all()
    return jsonify(
        {
            "topics": [
                {"slug": t.slug, "title": t.title, "path": f"/help/{t.slug}"}
                for t in rows
            ]
        }
    )


@api_bp.route("/help/topics/<slug>", methods=["GET"])
@login_required
def api_help_topic(slug):
    with SessionLocal() as db:
        topic = db.scalar(select(HelpTopic).where(HelpTopic.slug == slug))
    if topic is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(
        {"slug": topic.slug, "title": topic.title, "body": topic.body}
    )


# ── Admin ─────────────────────────────────────────────────────────────────────


@api_bp.route("/admin/summary", methods=["GET"])
@login_required
@admin_required
def api_admin_summary():
    return jsonify({"users": users_dict()})


@api_bp.route("/admin/users", methods=["POST"])
@login_required
@admin_required
def api_admin_users_post():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    name = (data.get("name") or "").strip()
    role = data.get("role", "Viewer")
    if not email or not password or not name:
        return jsonify({"error": "Email, password, and name are required."}), 400
    if role not in ("Admin", "Investigator", "Member", "Viewer"):
        return jsonify({"error": "Invalid role."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    try:
        register_user(email, password, name, role)
        return jsonify({"ok": True, "users": users_dict()})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/admin/assign", methods=["GET"])
@login_required
@admin_required
def api_admin_assign_get():
    with SessionLocal() as db:
        cases = db.scalars(select(ForensicCase).order_by(ForensicCase.id.desc())).all()
        user_rows = db.scalars(
            select(User).where(User.role.in_(("Investigator", "Member", "Viewer")))
        ).all()
        assignable_emails = [u.email for u in user_rows]
        assignments = db.scalars(
            select(CaseAssignment).order_by(CaseAssignment.created_at.desc())
        ).all()
    return jsonify(
        {
            "cases": [_case_json(c) for c in cases],
            "assignable_emails": assignable_emails,
            "users": users_dict(),
            "assignments": [
                {
                    "id": a.id,
                    "evidence_id": a.evidence_id,
                    "assignee_username": a.assignee_username,
                    "assigner_username": a.assigner_username,
                    "assignee_role": a.assignee_role,
                    "created_at": _dt_iso(a.created_at),
                }
                for a in assignments
            ],
        }
    )


@api_bp.route("/admin/assign", methods=["POST"])
@login_required
@admin_required
def api_admin_assign_post():
    data = request.get_json(silent=True) or {}
    evidence_id = data.get("evidence_id")
    try:
        evidence_id = int(evidence_id)
    except (TypeError, ValueError):
        evidence_id = None
    assignee = (data.get("assignee_username") or "").strip().lower()
    role = data.get("assignee_role", "Investigator")
    with SessionLocal() as db:
        user_rows = db.scalars(
            select(User).where(User.role.in_(("Investigator", "Member", "Viewer")))
        ).all()
        assignable_emails = [u.email for u in user_rows]
    if not evidence_id or not assignee or assignee not in assignable_emails:
        return jsonify({"error": "Evidence ID and valid assignee required."}), 400
    if role not in ("Investigator", "Member", "Viewer"):
        return jsonify({"error": "Invalid assignee role."}), 400
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
    return jsonify({"ok": True})


@api_bp.route("/admin/requests", methods=["GET"])
@login_required
@admin_required
def api_admin_requests_get():
    with SessionLocal() as db:
        reqs = db.scalars(
            select(CaseAccessRequest).order_by(CaseAccessRequest.created_at.desc())
        ).all()
    return jsonify(
        {
            "requests": [
                {
                    "id": r.id,
                    "evidence_id": r.evidence_id,
                    "requester_username": r.requester_username,
                    "status": r.status,
                    "notes": r.notes,
                    "created_at": _dt_iso(r.created_at),
                    "decided_at": _dt_iso(r.decided_at),
                    "decided_by": r.decided_by,
                }
                for r in reqs
            ]
        }
    )


@api_bp.route("/admin/requests/<int:rid>/decide", methods=["POST"])
@login_required
@admin_required
def api_admin_requests_decide(rid):
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    with SessionLocal() as db:
        r = db.get(CaseAccessRequest, rid)
        if not r:
            return jsonify({"error": "not found"}), 404
        if action == "approve":
            r.status = "approved"
            r.decided_by = session["user"]
            r.decided_at = utcnow()
        elif action == "reject":
            r.status = "rejected"
            r.decided_by = session["user"]
            r.decided_at = utcnow()
        else:
            return jsonify({"error": "action must be approve or reject"}), 400
        db.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/audit", methods=["GET"])
@login_required
@admin_required
def api_admin_audit():
    """Off-chain audit trail: user actions, uploads, verification attempts."""
    limit = request.args.get("limit", default=150, type=int) or 150
    limit = min(max(limit, 1), 500)
    with SessionLocal() as db:
        audit_rows = db.scalars(
            select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(limit)
        ).all()
        ver_rows = db.scalars(
            select(VerificationRecord)
            .order_by(VerificationRecord.created_at.desc())
            .limit(limit)
        ).all()
    return jsonify(
        {
            "audit": [
                {
                    "id": a.id,
                    "username": a.username,
                    "action": a.action,
                    "detail": a.detail,
                    "evidence_id": a.evidence_id,
                    "case_id": a.case_id,
                    "created_at": _dt_iso(a.created_at),
                }
                for a in audit_rows
            ],
            "verifications": [
                {
                    "id": v.id,
                    "evidence_id": v.evidence_id,
                    "success": v.success,
                    "username": v.username,
                    "created_at": _dt_iso(v.created_at),
                }
                for v in ver_rows
            ],
        }
    )

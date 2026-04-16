"""
app.py  –  Flask backend for Blockchain Chain of Custody (FYP)
Author  : M. Talha  |  Roll: fa-2022/BS/DFCS/075

Run:
    cd backend && python app.py
"""

import hashlib
import os
import time

from cryptography.fernet import Fernet
from flask import (
    Flask,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func, select
from werkzeug.utils import secure_filename

from api_routes import api_bp
from auth import login_required, role_required
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
    CaseEvidenceLink,
    ForensicCase,
    OffChainEvidenceMeta,
    SecurityAlert,
    SessionLocal,
    TransferRequest,
    init_db,
)
from features_routes import features_bp
from help_routes import help_bp
from users_config import USERS, all_usernames

# ── App Setup ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
KEY_FILE = os.path.join(BASE_DIR, "fernet.key")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "frontend", "templates"),
    static_folder=os.path.join(ROOT_DIR, "frontend", "static"),
)
app.secret_key = "fyp-blockchain-custody-secret-2024"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

init_db()
app.register_blueprint(help_bp)
app.register_blueprint(api_bp)
app.register_blueprint(features_bp)


@app.context_processor
def inject_nav_counts():
    if "user" not in session:
        return {}
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
    return {"nav_pending_transfers": pending, "nav_alerts_unack": unack}


ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "txt",
    "log",
    "docx",
    "xlsx",
    "csv",
    "zip",
    "pcap",
    "json",
}

if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        FERNET_KEY = f.read()
else:
    FERNET_KEY = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(FERNET_KEY)

fernet = Fernet(FERNET_KEY)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_optional_float(form, key):
    v = form.get(key, "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user and user["password"] == password:
            session["user"] = username
            session["role"] = user["role"]
            session["name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials. Try again.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/dashboard")
@login_required
def dashboard():
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
            flash(f"Blockchain read error: {e}", "warning")
    recent_alerts = []
    with SessionLocal() as db:
        recent_alerts = db.scalars(
            select(SecurityAlert)
            .order_by(SecurityAlert.created_at.desc())
            .limit(8)
        ).all()
    return render_template(
        "dashboard.html",
        status=status,
        stats=stats,
        recent_alerts=recent_alerts,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/upload", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Investigator")
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)

        file = request.files["file"]
        encrypt = request.form.get("encrypt") == "on"
        actor = session["name"]
        notes = request.form.get(
            "notes", "Evidence collected and recorded on blockchain"
        )
        case_id = request.form.get("case_id", type=int)

        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("File type not allowed.", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        raw_bytes = file.read()
        file_hash = sha256_bytes(raw_bytes)

        stored_bytes = fernet.encrypt(raw_bytes) if encrypt else raw_bytes
        save_name = ("enc_" + filename) if encrypt else filename
        save_path = os.path.join(UPLOAD_DIR, save_name)
        with open(save_path, "wb") as f:
            f.write(stored_bytes)

        if not blockchain_status()["deployed"]:
            flash("Blockchain not deployed. Run deploy.py first.", "danger")
            return redirect(request.url)

        try:
            account = get_ganache_account()
            ext = (
                filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
            )
            tx_hash = contract.functions.addEvidence(
                file_hash,
                filename,
                ext,
                len(raw_bytes),
                actor,
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
                                CaseEvidenceLink(
                                    case_id=case_id, evidence_id=ev_id
                                )
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

            flash(
                f"✅ Evidence #{ev_id} recorded on blockchain! "
                f"Hash: {file_hash[:20]}…",
                "success",
            )
            return redirect(url_for("evidence_detail", evidence_id=ev_id))
        except Exception as e:
            flash(f"Blockchain error: {e}", "danger")

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
    return render_template("upload.html", next_id=next_id, cases=cases)


# ══════════════════════════════════════════════════════════════════════════════
#  EVIDENCE LIST
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/evidence")
@login_required
def evidence_list():
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
            flash(f"Error fetching evidence: {e}", "warning")
    return render_template("evidence_list.html", items=items, status=status)


# ══════════════════════════════════════════════════════════════════════════════
#  EVIDENCE DETAIL
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/evidence/<int:evidence_id>")
@login_required
def evidence_detail(evidence_id):
    status = blockchain_status()
    ev_data, chain = None, []
    offchain = None
    integrity_score = None
    validation_ok, validation_issues = True, []
    suspicious_flags = []
    locked_view = False
    unlock_at = None

    if status["deployed"] and status["connected"]:
        try:
            raw = contract.functions.getEvidence(evidence_id).call()
            ev_data = {
                "id": raw[0],
                "fileHash": raw[1],
                "fileName": raw[2],
                "fileType": raw[3],
                "fileSize": raw[4],
                "uploadedBy": raw[5],
                "createdAt": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(raw[6])
                ),
                "encrypted": raw[8],
                "events": raw[9],
            }
            raw_chain = contract.functions.getCustodyChain(evidence_id).call()
            chain = [format_event(e) for e in raw_chain]
            validation_ok, validation_issues = validate_custody_chain(chain)
            with SessionLocal() as db:
                integrity_score = compute_integrity_score(db, evidence_id, chain)
            suspicious_flags = detect_suspicious_activity(evidence_id)
        except Exception as e:
            flash(f"Error: {e}", "danger")

    with SessionLocal() as db:
        offchain = db.get(OffChainEvidenceMeta, evidence_id)

    locked, unlock_at = is_evidence_locked(evidence_id)
    if locked and session.get("role") != "Admin":
        locked_view = True

    return render_template(
        "evidence_detail.html",
        evidence=ev_data,
        chain=chain,
        action_names=ACTION_NAMES,
        offchain=offchain,
        integrity_score=integrity_score,
        validation_ok=validation_ok,
        validation_issues=validation_issues,
        suspicious_flags=suspicious_flags,
        locked_view=locked_view,
        unlock_at=unlock_at,
        users_for_transfer=[u for u in all_usernames() if u != session["user"]],
    )


# ══════════════════════════════════════════════════════════════════════════════
#  LOG ACTION
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/evidence/<int:evidence_id>/action", methods=["POST"])
@login_required
def log_action(evidence_id):
    action_name = request.form.get("action")
    notes = request.form.get("notes", "")
    actor = session["name"]
    geo_lat = _parse_optional_float(request.form, "geo_lat")
    geo_lng = _parse_optional_float(request.form, "geo_lng")

    locked, _ = is_evidence_locked(evidence_id)
    if locked and session.get("role") != "Admin":
        flash("This evidence is time-locked. Only an Admin can act before unlock.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))

    if action_name not in ACTION_CODES:
        flash("Invalid action.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))

    if not role_can_log_action(session.get("role"), action_name):
        flash("Your role cannot perform this custody action.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))

    try:
        ev = contract.functions.getEvidence(evidence_id).call()
        acct = get_ganache_account()
        tx = contract.functions.logCustodyEvent(
            evidence_id,
            ev[1],
            ACTION_CODES[action_name],
            actor,
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
        flash(f"✅ Action '{action_name}' recorded on blockchain.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for("evidence_detail", evidence_id=evidence_id))


# ══════════════════════════════════════════════════════════════════════════════
#  VERIFY
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/verify", methods=["GET", "POST"])
@login_required
def verify():
    result = None
    if request.method == "POST":
        evidence_id = request.form.get("evidence_id", type=int)
        file = request.files.get("file")
        geo_lat = _parse_optional_float(request.form, "geo_lat")
        geo_lng = _parse_optional_float(request.form, "geo_lng")

        if not file or file.filename == "":
            flash("Please upload a file to verify.", "danger")
            return redirect(request.url)

        raw_bytes = file.read()
        new_hash = sha256_bytes(raw_bytes)

        try:
            authentic, stored_hash = contract.functions.verifyEvidence(
                evidence_id, new_hash
            ).call()
            ev = contract.functions.getEvidence(evidence_id).call()

            with SessionLocal() as db:
                record_verification(
                    db, evidence_id, authentic, session["user"]
                )
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
                        session["name"],
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

            result = {
                "authentic": authentic,
                "evidence_id": evidence_id,
                "file_name": ev[2],
                "new_hash": new_hash,
                "stored_hash": stored_hash,
            }
        except Exception as e:
            flash(f"Verification error: {e}", "danger")

    count = 0
    if blockchain_status()["deployed"]:
        try:
            count = contract.functions.getEvidenceCount().call()
        except Exception:
            pass

    return render_template("verify.html", result=result, evidence_count=count)


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Blockchain Chain of Custody – Flask Backend")
    print("  FYP by M. Talha  |  fa-2022/BS/DFCS/075")
    print("=" * 60)
    bs = blockchain_status()
    print(f"  Ganache connected : {bs['connected']}")
    print(f"  Contract deployed : {bs['deployed']}")
    if not bs["connected"]:
        print("  ⚠  Start Ganache on port 7545 first!")
    if not bs["deployed"]:
        print("  ⚠  Run  python deploy.py  to deploy the contract.")
    print("  Starting Flask on http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)

"""
app.py  –  Flask backend for Blockchain Chain of Custody (FYP)
Author  : M. Talha  |  Roll: fa-2022/BS/DFCS/075

Run:
    python app.py

Prerequisites:
    1. Ganache running on port 7545
    2. deploy.py executed at least once (generates contract_abi.json & contract_address.txt)
    3. pip install flask web3 cryptography
"""

import hashlib
import json
import os
import time
from functools import wraps

from cryptography.fernet import Fernet
from flask import (Flask, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.utils import secure_filename
from web3 import Web3

# ── App Setup ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(BASE_DIR)            # fyp/
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
KEY_FILE   = os.path.join(BASE_DIR, "fernet.key")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "frontend", "templates"),
    static_folder=os.path.join(ROOT_DIR, "frontend", "static"),
)
app.secret_key = "fyp-blockchain-custody-secret-2024"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "txt", "log",
                       "docx", "xlsx", "csv", "zip", "pcap", "json"}

# ── Encryption Key ─────────────────────────────────────────────────────────────
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        FERNET_KEY = f.read()
else:
    FERNET_KEY = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(FERNET_KEY)

fernet = Fernet(FERNET_KEY)

# ── Ganache / Web3 Setup ───────────────────────────────────────────────────────
GANACHE_URL   = "http://127.0.0.1:7545"
ABI_FILE      = os.path.join(BASE_DIR, "contract_abi.json")
ADDRESS_FILE  = os.path.join(BASE_DIR, "contract_address.txt")

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

def load_contract():
    if not os.path.exists(ABI_FILE) or not os.path.exists(ADDRESS_FILE):
        return None
    with open(ABI_FILE) as f:
        abi = json.load(f)
    with open(ADDRESS_FILE) as f:
        address = f.read().strip()
    return w3.eth.contract(address=address, abi=abi)

contract = load_contract()

# ── Helpers ────────────────────────────────────────────────────────────────────
ACTION_NAMES = {0: "Collected", 1: "Transferred", 2: "Analyzed",
                3: "Verified", 4: "Archived"}
ACTION_CODES = {v: k for k, v in ACTION_NAMES.items()}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def get_ganache_account():
    """Return first Ganache account (acting as the logged-in user's wallet)."""
    return w3.eth.accounts[0] if w3.eth.accounts else None

def format_event(ev):
    """Convert a raw tuple event from the contract into a dict."""
    action_id = ev[3] if isinstance(ev[3], int) else int(ev[3])
    return {
        "evidenceId": ev[0],
        "fileHash":   ev[1],
        "fileName":   ev[2],
        "action":     ACTION_NAMES.get(action_id, "Unknown"),
        "actor":      ev[4],
        "notes":      ev[5],
        "timestamp":  ev[6],
        "datetime":   time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev[6])),
    }

def blockchain_status():
    connected = w3.is_connected()
    deployed  = contract is not None
    return {"connected": connected, "deployed": deployed}

# ── Mock user store (extend with DB for production) ────────────────────────────
USERS = {
    "admin":     {"password": "admin123",     "role": "Admin",      "name": "Admin User"},
    "investigator": {"password": "inv123",    "role": "Investigator","name": "Ali Investigator"},
    "analyst":   {"password": "analyst123",   "role": "Analyst",    "name": "Sara Analyst"},
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
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
            session["user"]     = username
            session["role"]     = user["role"]
            session["name"]     = user["name"]
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
                recent.append({
                    "id":        ev[0],
                    "fileName":  ev[2],
                    "fileType":  ev[3],
                    "uploadedBy":ev[5],
                    "createdAt": time.strftime("%Y-%m-%d %H:%M", time.localtime(ev[6])),
                    "encrypted": ev[8],
                    "events":    ev[9],
                })
            stats["recent"] = list(reversed(recent))
        except Exception as e:
            flash(f"Blockchain read error: {e}", "warning")
    return render_template("dashboard.html", status=status, stats=stats)

# ══════════════════════════════════════════════════════════════════════════════
#  EVIDENCE – Upload
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)

        file      = request.files["file"]
        encrypt   = request.form.get("encrypt") == "on"
        actor     = session["name"]
        notes     = request.form.get("notes", "Evidence collected and recorded on blockchain")

        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("File type not allowed.", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        raw_bytes = file.read()

        # SHA-256 of ORIGINAL file (before optional encryption)
        file_hash = sha256_bytes(raw_bytes)

        # Optionally encrypt
        stored_bytes = fernet.encrypt(raw_bytes) if encrypt else raw_bytes
        save_name    = ("enc_" + filename) if encrypt else filename
        save_path    = os.path.join(UPLOAD_DIR, save_name)
        with open(save_path, "wb") as f:
            f.write(stored_bytes)

        if not blockchain_status()["deployed"]:
            flash("Blockchain not deployed. Run deploy.py first.", "danger")
            return redirect(request.url)

        try:
            account  = get_ganache_account()
            ext      = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
            tx_hash  = contract.functions.addEvidence(
                file_hash,
                filename,
                ext,
                len(raw_bytes),
                actor,
                encrypt
            ).transact({"from": account, "gas": 3_000_000})
            w3.eth.wait_for_transaction_receipt(tx_hash)

            ev_id = contract.functions.getEvidenceCount().call()
            flash(
                f"✅ Evidence #{ev_id} recorded on blockchain! "
                f"Hash: {file_hash[:20]}…",
                "success"
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
    return render_template("upload.html", next_id=next_id)

# ══════════════════════════════════════════════════════════════════════════════
#  EVIDENCE – List
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
                items.append({
                    "id":        ev[0],
                    "fileHash":  ev[1],
                    "fileName":  ev[2],
                    "fileType":  ev[3],
                    "fileSize":  ev[4],
                    "uploadedBy":ev[5],
                    "createdAt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev[6])),
                    "encrypted": ev[8],
                    "events":    ev[9],
                })
            items = list(reversed(items))
        except Exception as e:
            flash(f"Error fetching evidence: {e}", "warning")
    return render_template("evidence_list.html", items=items, status=status)

# ══════════════════════════════════════════════════════════════════════════════
#  EVIDENCE – Detail / Chain of Custody
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/evidence/<int:evidence_id>")
@login_required
def evidence_detail(evidence_id):
    status = blockchain_status()
    ev_data, chain = None, []
    if status["deployed"] and status["connected"]:
        try:
            raw  = contract.functions.getEvidence(evidence_id).call()
            ev_data = {
                "id":        raw[0],
                "fileHash":  raw[1],
                "fileName":  raw[2],
                "fileType":  raw[3],
                "fileSize":  raw[4],
                "uploadedBy":raw[5],
                "createdAt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(raw[6])),
                "encrypted": raw[8],
                "events":    raw[9],
            }
            raw_chain = contract.functions.getCustodyChain(evidence_id).call()
            chain = [format_event(e) for e in raw_chain]
        except Exception as e:
            flash(f"Error: {e}", "danger")
    return render_template("evidence_detail.html",
                           evidence=ev_data, chain=chain,
                           action_names=ACTION_NAMES)

# ══════════════════════════════════════════════════════════════════════════════
#  LOG CUSTODY ACTION
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/evidence/<int:evidence_id>/action", methods=["POST"])
@login_required
def log_action(evidence_id):
    action_name = request.form.get("action")
    notes       = request.form.get("notes", "")
    actor       = session["name"]

    if action_name not in ACTION_CODES:
        flash("Invalid action.", "danger")
        return redirect(url_for("evidence_detail", evidence_id=evidence_id))

    try:
        ev    = contract.functions.getEvidence(evidence_id).call()
        acct  = get_ganache_account()
        tx    = contract.functions.logCustodyEvent(
            evidence_id,
            ev[1],                      # current stored hash
            ACTION_CODES[action_name],
            actor,
            notes
        ).transact({"from": acct, "gas": 1_000_000})
        w3.eth.wait_for_transaction_receipt(tx)
        flash(f"✅ Action '{action_name}' recorded on blockchain.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for("evidence_detail", evidence_id=evidence_id))

# ══════════════════════════════════════════════════════════════════════════════
#  VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/verify", methods=["GET", "POST"])
@login_required
def verify():
    result = None
    if request.method == "POST":
        evidence_id = request.form.get("evidence_id", type=int)
        file        = request.files.get("file")

        if not file or file.filename == "":
            flash("Please upload a file to verify.", "danger")
            return redirect(request.url)

        raw_bytes = file.read()
        new_hash  = sha256_bytes(raw_bytes)

        try:
            authentic, stored_hash = contract.functions.verifyEvidence(
                evidence_id, new_hash
            ).call()
            ev = contract.functions.getEvidence(evidence_id).call()

            # Log verification event on chain
            acct = get_ganache_account()
            contract.functions.logCustodyEvent(
                evidence_id, new_hash,
                ACTION_CODES["Verified"],
                session["name"],
                "Integrity verification performed"
            ).transact({"from": acct, "gas": 1_000_000})

            result = {
                "authentic":   authentic,
                "evidence_id": evidence_id,
                "file_name":   ev[2],
                "new_hash":    new_hash,
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
#  API – JSON endpoints (for AJAX / future mobile)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/status")
def api_status():
    return jsonify(blockchain_status())

@app.route("/api/evidence")
@login_required
def api_evidence():
    items = []
    try:
        count = contract.functions.getEvidenceCount().call()
        for eid in range(1, count + 1):
            ev = contract.functions.getEvidence(eid).call()
            items.append({"id": ev[0], "fileName": ev[2], "hash": ev[1]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(items)

@app.route("/api/evidence/<int:evidence_id>/chain")
@login_required
def api_chain(evidence_id):
    try:
        raw = contract.functions.getCustodyChain(evidence_id).call()
        return jsonify([format_event(e) for e in raw])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

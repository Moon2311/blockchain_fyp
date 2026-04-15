"""JSON API blueprint (separate functions per endpoint)."""

from flask import Blueprint, jsonify

from auth import login_required
from blockchain_utils import blockchain_status, contract, format_event

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/status")
def api_status():
    return jsonify(blockchain_status())


@api_bp.route("/evidence")
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


@api_bp.route("/evidence/<int:evidence_id>/chain")
@login_required
def api_chain(evidence_id):
    try:
        raw = contract.functions.getCustodyChain(evidence_id).call()
        return jsonify([format_event(e) for e in raw])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

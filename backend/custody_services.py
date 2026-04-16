"""Auditing, RBAC helpers, integrity scoring, chain validation, alerts, HMAC action signatures."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import (
    AuditLogEntry,
    SecurityAlert,
    SessionLocal,
    VerificationRecord,
    utcnow,
)

# Role-based action permissions for on-chain custody actions (by display name)
ACTION_ROLE_MATRIX: dict[str, tuple[str, ...]] = {
    "Transferred": ("Admin", "Investigator"),
    "Analyzed": ("Admin", "Investigator", "Analyst"),
    "Verified": ("Admin", "Investigator", "Analyst"),
    "Archived": ("Admin", "Investigator"),
}


def role_can_log_action(role: str, action_name: str) -> bool:
    allowed = ACTION_ROLE_MATRIX.get(action_name)
    if not allowed:
        return True
    return role in allowed


def sign_action_hmac(
    app_secret: str, username: str, evidence_id: int, action: str, notes: str
) -> str:
    msg = f"{username}|{evidence_id}|{action}|{notes}".encode("utf-8")
    return hmac.new(app_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def log_audit(
    session: Session,
    *,
    username: str,
    action: str,
    detail: str | None = None,
    evidence_id: int | None = None,
    case_id: int | None = None,
    geo_lat: float | None = None,
    geo_lng: float | None = None,
    signature_hex: str | None = None,
) -> None:
    session.add(
        AuditLogEntry(
            username=username,
            action=action,
            detail=detail,
            evidence_id=evidence_id,
            case_id=case_id,
            geo_lat=geo_lat,
            geo_lng=geo_lng,
            signature_hex=signature_hex,
        )
    )


def add_security_alert(
    session: Session,
    *,
    level: str,
    code: str,
    message: str,
    evidence_id: int | None = None,
) -> None:
    session.add(
        SecurityAlert(
            level=level,
            code=code,
            message=message,
            evidence_id=evidence_id,
        )
    )


def record_verification(
    session: Session, evidence_id: int, success: bool, username: str
) -> None:
    session.add(
        VerificationRecord(
            evidence_id=evidence_id,
            success=success,
            username=username,
        )
    )


def validate_custody_chain(chain: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Heuristic chain validation: first event and transfer volume."""
    issues: list[str] = []
    if not chain:
        issues.append("No custody events recorded.")
        return False, issues
    actions = [c.get("action") for c in chain]
    if actions[0] != "Collected":
        issues.append("First event should be 'Collected'.")
    transfer_count = sum(1 for a in actions if a == "Transferred")
    if transfer_count > 8:
        issues.append("Unusually high number of transfer events — review custody policy.")
    return len(issues) == 0, issues


def compute_integrity_score(
    session: Session,
    evidence_id: int,
    chain: list[dict[str, Any]],
) -> float:
    """Score 0–100 from verification history and chain complexity."""
    fails = session.scalar(
        select(func.count())
        .select_from(VerificationRecord)
        .where(
            VerificationRecord.evidence_id == evidence_id,
            VerificationRecord.success.is_(False),
        )
    ) or 0
    oks = session.scalar(
        select(func.count())
        .select_from(VerificationRecord)
        .where(
            VerificationRecord.evidence_id == evidence_id,
            VerificationRecord.success.is_(True),
        )
    ) or 0
    transfers = sum(1 for c in chain if c.get("action") == "Transferred")
    score = 100.0
    score -= min(40.0, float(fails) * 20.0)
    score -= min(25.0, max(0.0, float(transfers) - 2.0) * 3.0)
    if oks > 0 and fails == 0:
        score = min(100.0, score + 5.0)
    if fails > 0 and oks > 0:
        score -= 5.0
    return max(0.0, min(100.0, round(score, 1)))


def detect_suspicious_activity(evidence_id: int) -> list[str]:
    """Flags based on recent audit frequency (off-chain)."""
    flags: list[str] = []
    since = utcnow() - timedelta(hours=24)
    with SessionLocal() as session:
        n = session.scalar(
            select(func.count())
            .select_from(AuditLogEntry)
            .where(
                AuditLogEntry.evidence_id == evidence_id,
                AuditLogEntry.created_at >= since,
            )
        )
        tcount = session.scalar(
            select(func.count())
            .select_from(AuditLogEntry)
            .where(
                AuditLogEntry.evidence_id == evidence_id,
                AuditLogEntry.created_at >= since,
                AuditLogEntry.action == "transfer_request",
            )
        )
    if n and n > 25:
        flags.append("Very high audit activity on this evidence in the last 24 hours.")
    if tcount and tcount > 5:
        flags.append("Many transfer requests in 24 hours — possible policy abuse.")
    return flags


def is_evidence_locked(evidence_id: int) -> tuple[bool, datetime | None]:
    from database import EvidenceTimeLock

    with SessionLocal() as session:
        row = session.get(EvidenceTimeLock, evidence_id)
        if row is None:
            return False, None
        now = utcnow()
        if row.unlock_at.tzinfo is None:
            unlock = row.unlock_at.replace(tzinfo=timezone.utc)
        else:
            unlock = row.unlock_at
        return now < unlock, unlock


def try_ipfs_add_file(_file_path: str) -> str | None:
    """Optional IPFS upload — set IPFS_API_URL to enable (stub returns None)."""
    import os

    if not os.environ.get("IPFS_API_URL"):
        return None
    # Production: POST multipart to IPFS HTTP API; omitted for offline FYP default.
    return None

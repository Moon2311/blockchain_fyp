"""SQLite via SQLAlchemy ORM — help topics, cases, audits, transfers, alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "custody.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class HelpTopic(Base):
    __tablename__ = "help_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class AppMeta(Base):
    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)


class ForensicCase(Base):
    __tablename__ = "forensic_cases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    links: Mapped[list["CaseEvidenceLink"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class CaseEvidenceLink(Base):
    __tablename__ = "case_evidence_links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("forensic_cases.id"), nullable=False)
    evidence_id: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    case: Mapped["ForensicCase"] = relationship(back_populates="links")


class CaseAssignment(Base):
    """Admin assigns an evidence record to Investigator or Member (role-scoped)."""

    __tablename__ = "case_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evidence_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    assignee_username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    assigner_username: Mapped[str] = mapped_column(String(128), nullable=False)
    assignee_role: Mapped[str] = mapped_column(String(32), nullable=False)  # Investigator | Member
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class CaseAccessRequest(Base):
    """Member requests access to a case; Admin approves."""

    __tablename__ = "case_access_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evidence_id: Mapped[int] mapped_column(Integer, nullable=False, index=True)
    requester_username: Mapped[str] mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] mapped_column(String(32), default="pending", index=True)
    notes: Mapped[str | None] mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    decided_at: Mapped[datetime | None] mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] mapped_column(String(128), nullable=True)


class OffChainEvidenceMeta(Base):
    """Hybrid storage: blockchain hash + local path / optional IPFS CID."""

    __tablename__ = "offchain_evidence_meta"

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relative_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ipfs_cid: Mapped[str | None] = mapped_column(String(256), nullable=True)
    storage_mode: Mapped[str] = mapped_column(String(32), default="local")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class TransferRequest(Base):
    """Two-step custody transfer: request → approve/reject."""

    __tablename__ = "transfer_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evidence_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    from_username: Mapped[str] = mapped_column(String(128), nullable=False)
    to_username: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class AuditLogEntry(Base):
    """Off-chain audit mirror with geo and action signature (HMAC)."""

    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    case_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    signature_hex: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evidence_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class EvidenceTimeLock(Base):
    __tablename__ = "evidence_time_locks"

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unlock_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    set_by: Mapped[str] = mapped_column(String(128), nullable=False)


def _seed_help(session: Session) -> None:
    rows = [
        (
            "overview",
            "Overview",
            "<p>This system records digital evidence metadata and custody events on a local Ethereum "
            "blockchain (Ganache). Uploads can be encrypted at rest with Fernet.</p>",
        ),
        (
            "upload",
            "Upload evidence",
            "<p>Choose a file, optional encryption, and notes. The SHA-256 hash of the original file "
            "is stored on-chain together with filename, type, size, and uploader.</p>",
        ),
        (
            "evidence",
            "Evidence list & detail",
            "<p>Browse all evidence IDs, open a record to see metadata and the full custody chain "
            "pulled from the contract.</p>",
        ),
        (
            "verify",
            "Verify integrity",
            "<p>Re-hash a file and compare it to the hash recorded for an evidence ID. A verification "
            "event can be logged on-chain.</p>",
        ),
        (
            "blockchain",
            "Blockchain setup",
            "<p>Run Ganache on port 7545, deploy the contract with <code>deploy.py</code>, and ensure "
            "<code>contract_abi.json</code> and <code>contract_address.txt</code> exist in the backend folder.</p>",
        ),
        (
            "api",
            "JSON API",
            "<p>Endpoints under <code>/api</code>: <code>/api/status</code> (public), "
            "<code>/api/evidence</code> and <code>/api/evidence/&lt;id&gt;/chain</code> (login required).</p>",
        ),
    ]
    for slug, title, body in rows:
        session.add(HelpTopic(slug=slug, title=title, body=body))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        n = session.scalar(select(func.count()).select_from(HelpTopic))
        if n == 0:
            _seed_help(session)
            session.commit()

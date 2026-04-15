"""SQLite via SQLAlchemy ORM (help content and app metadata)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "custody.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class HelpTopic(Base):
    __tablename__ = "help_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(nullable=False)


class AppMeta(Base):
    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str | None] = mapped_column(nullable=True)


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

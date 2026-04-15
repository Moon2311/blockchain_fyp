"""Help pages: one view function per topic; content from SQLAlchemy models."""

from flask import Blueprint, abort, render_template
from sqlalchemy import select

from auth import login_required
from database import HelpTopic, SessionLocal

help_bp = Blueprint("help", __name__)

SLUG_TO_ENDPOINT = {
    "overview": "help.help_overview",
    "upload": "help.help_upload",
    "evidence": "help.help_evidence",
    "verify": "help.help_verify",
    "blockchain": "help.help_blockchain",
    "api": "help.help_api",
}


def _topic_or_404(slug: str) -> dict:
    with SessionLocal() as session:
        topic = session.scalar(select(HelpTopic).where(HelpTopic.slug == slug))
    if topic is None:
        abort(404)
    return {"slug": topic.slug, "title": topic.title, "body": topic.body}


@help_bp.route("/help")
@login_required
def help_index():
    with SessionLocal() as session:
        rows = session.scalars(select(HelpTopic).order_by(HelpTopic.id)).all()
    topics = []
    for t in rows:
        topics.append(
            {
                "slug": t.slug,
                "title": t.title,
                "endpoint": SLUG_TO_ENDPOINT.get(t.slug),
            }
        )
    return render_template("help/index.html", topics=topics)


@help_bp.route("/help/overview")
@login_required
def help_overview():
    topic = _topic_or_404("overview")
    return render_template("help/topic.html", topic=topic)


@help_bp.route("/help/upload")
@login_required
def help_upload():
    topic = _topic_or_404("upload")
    return render_template("help/topic.html", topic=topic)


@help_bp.route("/help/evidence")
@login_required
def help_evidence():
    topic = _topic_or_404("evidence")
    return render_template("help/topic.html", topic=topic)


@help_bp.route("/help/verify")
@login_required
def help_verify():
    topic = _topic_or_404("verify")
    return render_template("help/topic.html", topic=topic)


@help_bp.route("/help/blockchain")
@login_required
def help_blockchain():
    topic = _topic_or_404("blockchain")
    return render_template("help/topic.html", topic=topic)


@help_bp.route("/help/api")
@login_required
def help_api():
    topic = _topic_or_404("api")
    return render_template("help/topic.html", topic=topic)

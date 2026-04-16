"""User accounts — loaded from SQLite (see database.User)."""

from sqlalchemy import select

from database import SessionLocal, User

# Rebuilt from DB on first access
_USERS_CACHE: dict | None = None


def _load_users_cache() -> dict:
    global _USERS_CACHE
    if _USERS_CACHE is None:
        with SessionLocal() as session:
            rows = session.scalars(select(User).order_by(User.id)).all()
            _USERS_CACHE = {
                u.email: {
                    "password": "",  # never used when using DB auth
                    "role": u.role,
                    "name": u.name,
                    "id": u.id,
                }
                for u in rows
            }
    return _USERS_CACHE


def users_dict() -> dict:
    """All users: email -> user dict (for templates)."""
    return _load_users_cache()


def all_usernames() -> list[str]:
    return sorted(users_dict().keys())


def get_user_by_id(user_id: int) -> User | None:
    with SessionLocal() as session:
        return session.get(User, user_id)


def get_user_by_email(email: str) -> User | None:
    with SessionLocal() as session:
        return session.scalar(select(User).where(User.email == email))


def invalidate_users_cache() -> None:
    """Call after creating/updating users in the database."""
    global _USERS_CACHE
    _USERS_CACHE = None

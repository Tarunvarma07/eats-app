"""
DB-backed JWT token blacklist for logout revocation.

Replaces the previous in-memory set which was cleared on every server
restart or Uvicorn --reload, causing logged-out tokens to become valid
again — the root cause of 'inconsistent auth' behaviour.

Each revoked JTI is stored in the `token_blacklist` table. All worker
processes share the same PostgreSQL database, so revocations are
immediately visible across all processes.
"""

from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.token_blacklist import TokenBlacklist


def add_to_blacklist(jti: str, expires_at: datetime | None = None) -> None:
    """Persist a revoked JTI to the database."""
    db = SessionLocal()
    try:
        entry = TokenBlacklist(
            jti=jti,
            revoked_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def is_blacklisted(jti: str) -> bool:
    """Return True if the JTI has been revoked."""
    db = SessionLocal()
    try:
        return db.query(TokenBlacklist).filter(
            TokenBlacklist.jti == jti
        ).first() is not None
    finally:
        db.close()

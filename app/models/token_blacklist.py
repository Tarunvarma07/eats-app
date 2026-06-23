from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime
from app.db.database import Base


class TokenBlacklist(Base):
    """
    Persisted JWT revocation list.

    Each row stores a JTI (JWT ID) that has been explicitly revoked
    (i.e. the user called /auth/logout). Rows whose expires_at is in
    the past are no longer needed and can be pruned by a maintenance job.

    Unlike the previous in-memory set, this table survives server
    restarts and is visible to all Uvicorn worker processes, fixing the
    'logged-out token becomes valid again after --reload' bug.
    """

    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), unique=True, nullable=False, index=True)
    revoked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)

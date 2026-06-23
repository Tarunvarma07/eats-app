from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    JSON
)
from sqlalchemy.sql import func

from app.db.database import Base


class AuditLog(Base):
    """
    Immutable audit trail. Every significant write action is recorded here.
    user_id is nullable to support system-generated events (e.g. stale session cleanup).
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who performed the action (NULL = system/scheduled job)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # e.g. "REGISTER", "LOGIN", "LOGOUT", "STALE_SESSION_CLOSED"
    action = Column(String(50), nullable=False, index=True)

    # e.g. "user", "attendance_session"
    entity = Column(String(50), nullable=False)

    # PK of the affected row (nullable for bulk actions)
    entity_id = Column(Integer, nullable=True)

    # Free-form JSON for extra context (email, IP, etc.)
    detail = Column(JSON, nullable=True)

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

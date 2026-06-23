"""
ActivityLog model — one row per heartbeat from the desktop agent.
Indexed on (session_id, timestamp) and (user_id, timestamp) for fast rollups.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(
        Integer,
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,       # denormalized for fast per-user queries
    )

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # "active" | "idle"
    status = Column(String(10), nullable=False)

    # Seconds since last keyboard/mouse event — only meaningful when status='idle'
    idle_seconds = Column(Integer, nullable=True)

    # Relationships (for ORM convenience — not required for queries)
    session = relationship("AttendanceSession", back_populates="activity_logs")
    user    = relationship("User",             back_populates="activity_logs")


# Composite indexes for the two main query patterns
Index("ix_activity_session_time", ActivityLog.session_id, ActivityLog.timestamp)
Index("ix_activity_user_time",    ActivityLog.user_id,    ActivityLog.timestamp)

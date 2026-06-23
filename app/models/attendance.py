"""
AttendanceSession — extended with activity monitoring + office/WFH columns.
The four new columns are additive; existing rows get NULL / default values.
"""
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Date,
    String,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    login_time = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    logout_time = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_minutes = Column(Integer, nullable=True)

    login_date = Column(Date, nullable=False)

    ip_address = Column(String(45), nullable=True)

    is_late = Column(Boolean, default=False, nullable=False)

    # ── Activity monitoring add-on columns ───────────────────────────────────
    # "office" | "remote" | "unknown"
    work_location = Column(String(10), default="unknown", nullable=True)

    # "auto" (IP-detected) | "manual" (employee override)
    location_source = Column(String(10), default="auto", nullable=True)

    # Cached totals — computed from ActivityLogs at logout time (nullable until first logout)
    active_minutes = Column(Integer, nullable=True)
    idle_minutes   = Column(Integer, nullable=True)

    # Relationships
    user          = relationship("User",        back_populates="attendance_sessions")
    activity_logs = relationship("ActivityLog", back_populates="session",
                                 cascade="all, delete-orphan")

    # Performance indexes for frequently queried columns
    __table_args__ = (
        Index("ix_attendance_user_date", "user_id", "login_date"),
        Index("ix_attendance_login_time", "login_time"),
        Index("ix_attendance_logout_time", "logout_time"),
    )
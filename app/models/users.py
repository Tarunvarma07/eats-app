from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(String(150), unique=True, nullable=False, index=True)

    hashed_password = Column(String(255), nullable=False)

    role = Column(String(20), default="employee", server_default="employee", nullable=False)

    department = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True, server_default="true")

    is_approved = Column(Boolean, default=False, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    attendance_sessions = relationship(
        "AttendanceSession",
        back_populates="user"
    )

    activity_logs = relationship(
        "ActivityLog",
        back_populates="user"
    )

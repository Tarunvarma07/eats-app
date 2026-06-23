import pytest
from app.models.users import User
from app.models.attendance import AttendanceSession
from app.models.activity_log import ActivityLog
from app.models.audit_log import AuditLog


def test_user_model_has_required_fields():
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
        role="employee",
        is_active=True
    )
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.hashed_password == "hashed"
    assert user.role == "employee"
    assert user.is_active is True


def test_user_model_defaults():
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
        role="employee",
        is_active=True
    )
    assert user.role == "employee"
    assert user.is_active is True
    assert user.department is None  # nullable


def test_attendance_session_model():
    from datetime import datetime, date
    session = AttendanceSession(
        user_id=1,
        login_time=datetime.utcnow(),
        login_date=date.today(),
        is_late=False
    )
    assert session.user_id == 1
    assert session.is_late is False
    assert session.logout_time is None  # nullable
    assert session.duration_minutes is None  # nullable


def test_activity_log_model():
    from datetime import datetime
    log = ActivityLog(
        session_id=1,
        user_id=1,
        timestamp=datetime.utcnow(),
        status="active",
        idle_seconds=0
    )
    assert log.session_id == 1
    assert log.user_id == 1
    assert log.status == "active"
    assert log.idle_seconds == 0


def test_audit_log_model():
    from datetime import datetime
    audit = AuditLog(
        user_id=1,
        action="login",
        entity="user",
        entity_id=1,
        detail={}
    )
    assert audit.user_id == 1
    assert audit.action == "login"
    assert audit.entity == "user"
    assert audit.entity_id == 1
    assert audit.detail == {}

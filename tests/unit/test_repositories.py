import pytest
from datetime import datetime, date
from app.repositories.user_repository import UserRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.activity_repository import ActivityRepository


def test_user_repository_find_by_email(db):
    from app.models.users import User
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    found = UserRepository.get_user_by_email(db, "test@example.com")
    assert found is not None
    assert found.email == "test@example.com"
    
    not_found = UserRepository.get_user_by_email(db, "nonexistent@example.com")
    assert not_found is None


def test_user_repository_find_by_id(db):
    from app.models.users import User
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    found = UserRepository.get_user_by_id(db, user.id)
    assert found is not None
    assert found.id == user.id


def test_attendance_repository_create_session(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    session = AttendanceSession(
        user_id=user.id,
        ip_address="127.0.0.1",
        work_location="office",
        login_time=datetime.utcnow(),
        login_date=date.today(),
        is_late=False
    )
    
    created = AttendanceRepository.create_session(db, session)
    assert created.user_id == user.id
    assert created.work_location == "office"
    assert created.logout_time is None


def test_attendance_repository_get_open_session(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    session = AttendanceSession(
        user_id=user.id,
        login_time=datetime.utcnow(),
        login_date=date.today(),
        is_late=False,
        work_location="office"
    )
    db.add(session)
    db.commit()
    
    open_session = AttendanceRepository.get_active_session(db, user.id)
    assert open_session is not None
    assert open_session.id == session.id


def test_activity_repository_insert_heartbeat(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from app.models.activity_log import ActivityLog
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    session = AttendanceSession(
        user_id=user.id,
        login_time=datetime.utcnow(),
        login_date=date.today(),
        is_late=False,
        work_location="office"
    )
    db.add(session)
    db.commit()
    
    ActivityRepository.insert_heartbeat(
        db,
        session_id=session.id,
        user_id=user.id,
        status="active",
        idle_seconds=0
    )
    
    heartbeat = db.query(ActivityLog).filter_by(session_id=session.id).first()
    assert heartbeat is not None
    assert heartbeat.status == "active"


def test_attendance_repository_update_session(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from app.core.security import hash_password
    from datetime import datetime, date, timezone
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    session = AttendanceSession(
        user_id=user.id,
        login_time=datetime.now(timezone.utc),
        login_date=date.today(),
        is_late=False,
        work_location="office"
    )
    db.add(session)
    db.commit()
    
    session.logout_time = datetime.now(timezone.utc)
    session.duration_minutes = 60
    
    updated = AttendanceRepository.update_session(db, session)
    assert updated.logout_time is not None
    assert updated.duration_minutes == 60


def test_user_repository_get_all_users(db):
    from app.models.users import User
    from app.core.security import hash_password
    
    user1 = User(
        email="test1@example.com",
        name="Test User 1",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        department="IT"
    )
    user2 = User(
        email="test2@example.com",
        name="Test User 2",
        hashed_password=hash_password("TestPassword123!"),
        role="admin",
        is_active=True,
        department="HR"
    )
    db.add(user1)
    db.add(user2)
    db.commit()
    
    users = UserRepository.get_all_users(db)
    assert len(users) >= 2

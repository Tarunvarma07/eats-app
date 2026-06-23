import pytest
from datetime import datetime, date
from app.services.activity_service import ActivityService
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.services.attendance_service import AttendanceService


def test_activity_service_record_heartbeat(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from datetime import datetime, date
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    # Create an open session first
    session = AttendanceSession(
        user_id=user.id,
        login_time=datetime.utcnow(),
        login_date=date.today(),
        is_late=False,
        work_location="office"
    )
    db.add(session)
    db.commit()
    
    result = ActivityService.record_heartbeat(db, user.id, "active", 0)
    assert result["recorded"] is True
    assert result["session_id"] == session.id


def test_activity_service_record_heartbeat_no_session(db):
    from app.models.users import User
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
        role="employee",
        is_active=True,
        department="IT"
    )
    db.add(user)
    db.commit()
    
    with pytest.raises(ValueError, match="No open attendance session"):
        ActivityService.record_heartbeat(db, user.id, "active", 0)


def test_auth_service_register_user(db):
    from app.schemas.users import UserCreate
    from app.core.security import hash_password
    
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password="TestPassword123!",
        department="IT"
    )
    
    result = AuthService.register_user(db, user_data)
    assert result.email == "test@example.com"
    assert result.name == "Test User"


def test_auth_service_register_duplicate_email(db):
    from app.schemas.users import UserCreate
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
    
    user_data = UserCreate(
        name="Test User 2",
        email="test@example.com",
        password="TestPassword123!",
        department="IT"
    )
    
    with pytest.raises(ValueError, match="Email already registered"):
        AuthService.register_user(db, user_data)


def test_attendance_service_get_user_history(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from datetime import datetime, date
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
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
    
    result = AttendanceService.get_attendance_history(db, user.id, None, None)
    assert len(result) == 1


def test_admin_service_get_dashboard_stats(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from datetime import datetime, date
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
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
    
    stats = AdminService.get_dashboard_stats(db)
    assert stats.total_employees == 1
    assert stats.currently_logged_in == 1


def test_admin_service_get_today_attendance(db):
    from app.models.users import User
    from app.models.attendance import AttendanceSession
    from datetime import datetime, date
    
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password="hashed",
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
    
    attendance = AdminService.get_today_attendance(db)
    assert len(attendance) == 1
    assert attendance[0].employee_id == user.id


def test_attendance_service_record_login(db):
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
    
    session = AttendanceService.record_login(db, user.id, "127.0.0.1", "office")
    assert session.user_id == user.id
    assert session.work_location == "office"
    assert session.logout_time is None


def test_activity_service_override_work_location(db):
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
    
    result = ActivityService.override_work_location(db, user.id, "home")
    assert result["work_location"] == "home"


def test_activity_service_override_work_location_no_session(db):
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
    
    with pytest.raises(ValueError, match="No open session"):
        ActivityService.override_work_location(db, user.id, "home")


def test_auth_service_authenticate_user_success(db):
    from app.models.users import User
    from app.core.security import hash_password
    from app.schemas.users import UserLogin
    
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
    
    login_data = UserLogin(email="test@example.com", password="TestPassword123!")
    authenticated = AuthService.authenticate_user(db, login_data)
    assert authenticated is not None
    assert authenticated.email == "test@example.com"


def test_auth_service_authenticate_user_wrong_password(db):
    from app.models.users import User
    from app.core.security import hash_password
    from app.schemas.users import UserLogin
    
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
    
    login_data = UserLogin(email="test@example.com", password="WrongPassword")
    with pytest.raises(ValueError, match="Invalid credentials"):
        AuthService.authenticate_user(db, login_data)

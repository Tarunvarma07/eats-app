import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set environment variable before importing app
os.environ["PYTEST_RUNNING"] = "1"

# Use in-memory SQLite for tests (fast, no external dependency)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Patch the production database SessionLocal and engine so that all modules
# (including core modules like token_blacklist) use the SQLite test database.
import app.db.database as db_module
db_module.SessionLocal = TestingSessionLocal
db_module.engine = engine

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.users import User


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    # Add attendance session columns for SQLite (mimicking PostgreSQL migration)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE attendance_sessions ADD COLUMN work_location VARCHAR(10) DEFAULT 'unknown'"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE attendance_sessions ADD COLUMN location_source VARCHAR(10) DEFAULT 'auto'"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE attendance_sessions ADD COLUMN active_minutes INTEGER"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE attendance_sessions ADD COLUMN idle_minutes INTEGER"))
        except Exception:
            pass
        conn.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Provide a fresh DB session per test, rolled back after."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db, monkeypatch):
    """TestClient with the test DB injected."""
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    # Skip startup tasks during tests
    monkeypatch.setenv("PYTEST_RUNNING", "1")
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db):
    """Create a regular employee user for tests."""
    user = User(
        email="testemployee@company.com",
        name="Test Employee",
        hashed_password=hash_password("TestPassword123!"),
        role="employee",
        is_active=True,
        is_approved=True,
        department="IT",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def test_admin(db):
    """Create an admin user for tests."""
    admin = User(
        email="admin@company.com",
        name="Test Admin",
        hashed_password=hash_password("AdminPassword123!"),
        role="admin",
        is_active=True,
        department="IT",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture()
def auth_headers(test_user):
    """JWT auth headers for a regular user."""
    token = create_access_token(data={"sub": test_user.email, "user_id": test_user.id, "role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_auth_headers(test_admin):
    """JWT auth headers for an admin user."""
    token = create_access_token(data={"sub": test_admin.email, "user_id": test_admin.id, "role": test_admin.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def inactive_employee(db):
    """Create an inactive employee user for tests."""
    user = User(
        email="inactive@test.com",
        name="Inactive User",
        hashed_password=hash_password("testpass123"),
        is_active=False,
        role="employee",
        department="IT"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

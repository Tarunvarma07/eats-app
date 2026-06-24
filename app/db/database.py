import logging
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)



engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,           # number of persistent connections
    max_overflow=20,        # extra connections beyond pool_size
    pool_timeout=30,        # seconds to wait for a connection
    pool_recycle=1800,      # recycle connections every 30 min (prevent stale)
    pool_pre_ping=True,     # test connection health before use
    echo=settings.LOG_LEVEL == "DEBUG"  # Only echo SQL in debug mode
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


# Dependency Injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Call this on app startup to verify DB is reachable. Returns True if successful, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as e:
        logger.critical(f"Database connection failed: {e}")
        return False
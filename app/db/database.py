import os
import logging
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

logger = logging.getLogger(__name__)


db_url_invalid = False
db_url_error = None
try:
    # Build engine arguments dynamically
    engine_kwargs = {
        "pool_pre_ping": True,
        "echo": settings.LOG_LEVEL == "DEBUG"
    }
    
    is_vercel = os.getenv("VERCEL") == "1"
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    
    if is_vercel or is_sqlite:
        # Serverless (Vercel) requires NullPool so Neon's proxy handles pooling.
        # SQLite also requires NullPool because it doesn't support QueuePool sizing.
        engine_kwargs["poolclass"] = NullPool
    else:
        # Standard connection pooling for long-running servers (e.g. Docker, Uvicorn)
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        engine_kwargs["pool_timeout"] = 30
        engine_kwargs["pool_recycle"] = 1800

    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
except Exception as e:
    logger.error(f"Error creating SQLAlchemy engine: {e}")
    # Fallback to an in-memory database to prevent crashes during imports/dry-runs
    engine = create_engine("sqlite:///:memory:")
    db_url_invalid = True
    db_url_error = str(e)


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
    if db_url_invalid:
        logger.critical("Database connection failed: Invalid DATABASE_URL configuration")
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as e:
        logger.critical(f"Database connection failed: {e}")
        return False
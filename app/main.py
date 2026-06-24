from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os
import time

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db.database import Base, engine, get_db, check_db_connection
from app.core.config import settings
from app.core.logging import setup_logging
from app.routers.auth import router as auth_router
from app.routers.attendance import router as attendance_router
from app.routers.admin import router as admin_router
from app.routers.activity import (
    heartbeat_router,
    admin_activity_router,
)

setup_logging()
logger = logging.getLogger(__name__)

# Import ALL models so SQLAlchemy registers them for Alembic
import app.models.users            # noqa: F401
import app.models.attendance       # noqa: F401
import app.models.audit_log        # noqa: F401
import app.models.token_blacklist  # noqa: F401  ← DB-backed JWT blacklist
import app.models.activity_log     # noqa: F401  ← Activity monitoring

# NOTE: Base.metadata.create_all() removed - schema now managed by Alembic migrations

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000)
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} duration={duration_ms}ms "
            f"ip={request.client.host}"
        )
        return response


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    check_db_connection()
    
    # Run startup tasks
    import os
    if os.getenv("PYTEST_RUNNING") != "1":
        from sqlalchemy import text
        from app.repositories.attendance_repository import AttendanceRepository

        # Add columns to attendance_sessions if they don't exist
        add_columns_sql = [
            """ALTER TABLE attendance_sessions
               ADD COLUMN IF NOT EXISTS work_location VARCHAR(10) DEFAULT 'unknown'""",
            """ALTER TABLE attendance_sessions
               ADD COLUMN IF NOT EXISTS location_source VARCHAR(10) DEFAULT 'auto'""",
            """ALTER TABLE attendance_sessions
               ADD COLUMN IF NOT EXISTS active_minutes INTEGER""",
            """ALTER TABLE attendance_sessions
               ADD COLUMN IF NOT EXISTS idle_minutes INTEGER""",
        ]

        with engine.begin() as conn:
            for sql in add_columns_sql:
                try:
                    conn.execute(text(sql))
                except Exception as exc:
                    print(f"[startup] Column migration skipped: {exc}")

        print("[startup] attendance_sessions schema migration complete.")

        # Close stale sessions
        db = next(get_db())
        try:
            closed = AttendanceRepository.close_stale_sessions(db, hours=12)
            if closed:
                print(f"[startup] Closed {closed} stale attendance session(s).")
        finally:
            db.close()
    
    yield
    # Shutdown (cleanup if needed)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Employee Attendance Tracking System",
    version="2.0.0",
    description=(
        "Tracks employee login/logout attendance with JWT auth, "
        "IST-aware late-login detection, full audit trail, "
        "activity monitoring, and office/WFH detection."
    ),
    lifespan=lifespan
)

# ── Middleware stack (outermost → innermost) ─────────────────────────────────

# 1. Request logging
app.add_middleware(RequestLoggingMiddleware)

# 2. GZip — compress all responses ≥ 1 KB (text, JSON, HTML, CSS, JS)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS — allow browser JS from same origin (and localhost dev ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,  # reads from .env
    allow_credentials=True,   # needed for httpOnly cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# 3. Trusted host — reject requests with spoofed Host headers
import os
allowed_hosts = ["localhost", "127.0.0.1", "*.localhost"]
if os.getenv("PYTEST_RUNNING") == "1":
    allowed_hosts.append("testserver")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)

# 4. Security headers — applied to every response
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Block clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Stop legacy XSS auditor from breaking valid pages
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Tell browsers to only use HTTPS (safe to set even on HTTP dev server)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    # Content Security Policy — allow Chart.js CDN for admin dashboard charts
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    # Cache-control for API responses (not for static files — StaticFiles sets its own)
    if request.url.path.startswith(("/auth", "/attendance", "/admin", "/activity")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response

# 5. Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Global Exception Handlers ───────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(loc) for loc in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Input validation failed",
            "details": details,
        },
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP_ERROR",
            "message": str(exc.detail),
            "details": [],
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log the full exception internally but NEVER expose it to the client
    logger.error(
        f"Unhandled exception on {request.method} {request.url}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "details": [],
        },
    )

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(attendance_router, prefix="/api/v1/attendance", tags=["attendance"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(heartbeat_router, prefix="/api/v1/activity", tags=["activity"])        # POST /activity/heartbeat
app.include_router(admin_activity_router, prefix="/api/v1/admin", tags=["admin"])   # GET  /admin/activity/*

# ── Static frontend ───────────────────────────────────────────────────────────
# Mounted LAST so API routes take priority over static file fallback
if os.path.isdir("frontend"):
    app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
else:
    logger.warning("Frontend directory not found. Static files mount skipped.")


# ── Health Check Endpoint ─────────────────────────────────────────────────────
from sqlalchemy import text

@app.get("/health", tags=["health"])
async def health_check(db = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    status = "ok" if db_status == "connected" else "degraded"
    status_code = 200 if db_status == "connected" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "db": db_status,
            "version": "1.0.0"
        }
    )


@app.get("/")
def root():
    return {
        "message": "Employee Attendance Tracking System API",
        "version": "2.0.0",
        "docs": "/docs",
        "app": "/app",
    }
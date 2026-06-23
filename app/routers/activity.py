"""
Activity router — employee heartbeat write + admin read endpoints.

Access control summary
  POST /activity/heartbeat          → employee JWT (own data only, user_id from token)
  POST /attendance/work-location    → employee JWT (own open session only)
  GET  /admin/activity/today        → admin JWT
  GET  /admin/activity/{user_id}    → admin JWT
  GET  /admin/report/activity/weekly  → admin JWT
  GET  /admin/report/activity/monthly → admin JWT

Employees have ZERO read endpoints for activity data — not even their own.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.schemas.activity import (
    HeartbeatRequest,
    ActivityTodayRow,
    ActivityHistoryRow,
    ActivityWeeklyRow,
    ActivityMonthlyRow,
)
from app.services.activity_service import ActivityService


# ── Router: employee heartbeat ─────────────────────────────────────────────────
heartbeat_router = APIRouter(tags=["Activity"])


@heartbeat_router.post(
    "/heartbeat",
    summary="Desktop agent heartbeat — employee write-only, admin-invisible to employee",
)
def post_heartbeat(
    body: HeartbeatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    The backend derives user_id from the JWT — the request body never contains it.
    Returns 409 if no open AttendanceSession exists for this user.
    """
    try:
        return ActivityService.record_heartbeat(
            db=db,
            user_id=current_user["user_id"],
            status=body.status,
            idle_seconds=body.idle_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ── Router: admin activity ─────────────────────────────────────────────────────
admin_activity_router = APIRouter(tags=["Admin — Activity"])


@admin_activity_router.get(
    "/activity/today",
    response_model=list[ActivityTodayRow],
    summary="Live activity view for all employees today (admin only)",
)
def get_today_activity(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ActivityService.get_today_activity(db)


@admin_activity_router.get(
    "/monitoring/status",
    summary="Current monitoring status of all employees (admin only)",
)
def get_monitoring_status(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Returns current status of all employees with their activity state."""
    return ActivityService.get_today_activity(db)


@admin_activity_router.get(
    "/activity/{user_id}",
    response_model=list[ActivityHistoryRow],
    summary="Full activity history for one employee — session by session (admin only)",
)
def get_user_activity(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ActivityService.get_user_activity(db, user_id)


@admin_activity_router.get(
    "/report/activity/weekly",
    response_model=list[ActivityWeeklyRow],
    summary="Weekly activity report: avg active%, office vs remote days (admin only)",
)
def get_weekly_activity(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ActivityService.get_weekly_activity(db)


@admin_activity_router.get(
    "/report/activity/monthly",
    response_model=list[ActivityMonthlyRow],
    summary="Monthly activity report (admin only)",
)
def get_monthly_activity(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ActivityService.get_monthly_activity(db, year=year, month=month)

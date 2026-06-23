"""
Pydantic schemas for the Activity Monitoring add-on.
"""
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


# ── Inbound (from desktop agent) ──────────────────────────────────────────────

class HeartbeatRequest(BaseModel):
    """
    Desktop agent sends this every 60-120 seconds.
    user_id is NEVER accepted from the client — derived from JWT.
    """
    status: Literal["active", "idle"] = Field(
        ..., description="'active' if user showed input in the last interval, 'idle' otherwise"
    )
    idle_seconds: Optional[int] = Field(
        None, ge=0, description="Seconds since last keyboard/mouse event (idle only)"
    )


class WorkLocationOverride(BaseModel):
    """Employee manually corrects their own session's office/WFH classification."""
    work_location: Literal["office", "remote"] = Field(
        ..., description="'office' or 'remote'"
    )


# ── Outbound (admin views) ────────────────────────────────────────────────────

class ActivityTodayRow(BaseModel):
    """One row in GET /admin/activity/today — live view."""
    user_id: int
    name: str
    department: Optional[str]
    work_location: str          # "office" | "remote" | "unknown"
    location_source: str        # "auto" | "manual"
    login_time: datetime
    logout_time: Optional[datetime]
    total_logged_minutes: int   # wall-clock minutes since login
    active_minutes: int         # computed from ActivityLogs (or cached for closed)
    idle_minutes: int
    active_percent: float
    last_heartbeat: Optional[datetime]
    heartbeat_status: Optional[str]   # "active" | "idle" — last known status
    session_status: str               # "Active" | "Logged Out"

    model_config = {"from_attributes": True}


class ActivityHistoryRow(BaseModel):
    """One row in GET /admin/activity/{user_id} — per-session drill-down."""
    session_id: int
    login_time: datetime
    logout_time: Optional[datetime]
    work_location: str
    location_source: str
    active_minutes: int
    idle_minutes: int
    active_percent: float
    total_heartbeats: int

    model_config = {"from_attributes": True}


class ActivityWeeklyRow(BaseModel):
    """Weekly activity report — augments the existing WeeklyReportRow."""
    employee_id: int
    name: str
    department: Optional[str]
    total_hours: str
    avg_active_percent: float
    office_days: int
    remote_days: int
    unknown_days: int

    model_config = {"from_attributes": True}


class ActivityMonthlyRow(BaseModel):
    """Monthly activity report."""
    employee_id: int
    name: str
    department: Optional[str]
    total_hours: str
    avg_active_percent: float
    office_days: int
    remote_days: int
    unknown_days: int

    model_config = {"from_attributes": True}

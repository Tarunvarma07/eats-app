from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel


class AttendanceHistoryResponse(BaseModel):

    session_id: int

    login_date: date

    login_time: datetime

    logout_time: datetime | None

    duration: str

    is_late: bool

    model_config = {
        "from_attributes": True
    }


class AdminAttendanceRow(BaseModel):
    """One row in the admin today's / history attendance table."""

    session_id: int
    employee_id: int
    name: str
    department: Optional[str]
    login_time: datetime
    logout_time: Optional[datetime]
    duration: str       # "Active" | "Xh Ym"
    is_late: bool
    status: str         # "Active" | "Logged Out" | "Late"

    model_config = {"from_attributes": True}


class WeeklyReportRow(BaseModel):
    """One row in the weekly hours report."""

    employee_id: int
    name: str
    department: Optional[str]
    total_minutes: int
    total_hours: str    # human-readable "Xh Ym"
    session_count: int

    model_config = {"from_attributes": True}


class MonthlyReportRow(BaseModel):
    """One row in the monthly hours report."""

    employee_id: int
    name: str
    department: Optional[str]
    total_minutes: int
    total_hours: str
    session_count: int

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    """Summary statistics card data for the admin dashboard header."""

    total_employees: int
    currently_logged_in: int
    late_today: int
    avg_hours_today: str    # "Xh Ym"
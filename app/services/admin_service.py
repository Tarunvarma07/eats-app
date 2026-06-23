from datetime import date, datetime, timezone, timedelta
from typing import Optional
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceSession
from app.models.users import User
from app.schemas.attendance import (
    AdminAttendanceRow,
    DashboardStats,
    WeeklyReportRow,
    MonthlyReportRow,
)

logger = logging.getLogger(__name__)


def _fmt(minutes: int) -> str:
    return f"{minutes // 60}h {minutes % 60}m"


def _build_row(session: AttendanceSession, user: User) -> AdminAttendanceRow:
    if session.logout_time is None:
        duration = "Active"
        status = "Late" if session.is_late else "Active"
    else:
        duration = _fmt(session.duration_minutes or 0)
        status = "Late" if session.is_late else "Logged Out"

    return AdminAttendanceRow(
        session_id=session.id,
        employee_id=user.id,
        name=user.name,
        department=str(user.department) if user.department else None,
        login_time=session.login_time,
        logout_time=session.logout_time,
        duration=duration,
        is_late=session.is_late,
        status=status,
    )


class AdminService:

    @staticmethod
    def get_today_attendance(
        db: Session,
        department: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[AdminAttendanceRow]:
        """All sessions whose login_date is today (local calendar date in UTC)."""
        today = datetime.now(timezone.utc).date()
        query = (
            db.query(AttendanceSession, User)
            .join(User, AttendanceSession.user_id == User.id)
            .filter(AttendanceSession.login_date == today)
        )
        
        if department:
            query = query.filter(User.department == department)
        
        if status:
            if status == 'Active':
                query = query.filter(AttendanceSession.logout_time.is_(None))
            elif status == 'Logged Out':
                query = query.filter(AttendanceSession.logout_time.isnot(None))
            elif status == 'Late':
                query = query.filter(AttendanceSession.is_late == True)
        
        rows = query.order_by(AttendanceSession.login_time.desc()).all()
        return [_build_row(s, u) for s, u in rows]

    @staticmethod
    def get_employee_history(
        db: Session, user_id: int
    ) -> list[AdminAttendanceRow]:
        """Full session history for one employee."""
        rows = (
            db.query(AttendanceSession, User)
            .join(User, AttendanceSession.user_id == User.id)
            .filter(AttendanceSession.user_id == user_id)
            .order_by(AttendanceSession.login_time.desc())
            .all()
        )
        return [_build_row(s, u) for s, u in rows]

    @staticmethod
    def get_dashboard_stats(db: Session) -> DashboardStats:
        """Summary stat cards: total employees, logged-in, late today, avg hours."""
        today = datetime.now(timezone.utc).date()

        total_employees = db.query(func.count(User.id)).filter(
            User.is_active == True
        ).scalar() or 0

        currently_logged_in = db.query(func.count(AttendanceSession.id)).filter(
            AttendanceSession.logout_time.is_(None)
        ).scalar() or 0

        late_today = db.query(func.count(AttendanceSession.id)).filter(
            AttendanceSession.login_date == today,
            AttendanceSession.is_late == True,
        ).scalar() or 0

        # Average hours for completed sessions today
        completed = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.login_date == today,
                AttendanceSession.logout_time.isnot(None),
            )
            .all()
        )
        if completed:
            avg_min = sum(
                (s.duration_minutes or 0) for s in completed
            ) // len(completed)
        else:
            avg_min = 0

        return DashboardStats(
            total_employees=total_employees,
            currently_logged_in=currently_logged_in,
            late_today=late_today,
            avg_hours_today=_fmt(avg_min),
        )

    @staticmethod
    def get_weekly_report(db: Session) -> list[WeeklyReportRow]:
        """Total hours per employee for the current calendar week (Mon–today)."""
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())  # Monday

        sessions = (
            db.query(AttendanceSession, User)
            .join(User, AttendanceSession.user_id == User.id)
            .filter(
                AttendanceSession.login_date >= week_start,
                AttendanceSession.logout_time.isnot(None),
            )
            .all()
        )

        # Aggregate per user
        agg: dict[int, dict] = {}
        for s, u in sessions:
            if u.id not in agg:
                agg[u.id] = {
                    "name": u.name,
                    "department": str(u.department) if u.department else None,
                    "total_minutes": 0,
                    "session_count": 0,
                }
            agg[u.id]["total_minutes"] += s.duration_minutes or 0
            agg[u.id]["session_count"] += 1

        return [
            WeeklyReportRow(
                employee_id=uid,
                name=v["name"],
                department=v["department"],
                total_minutes=v["total_minutes"],
                total_hours=_fmt(v["total_minutes"]),
                session_count=v["session_count"],
            )
            for uid, v in sorted(agg.items(), key=lambda x: x[1]["name"])
        ]

    @staticmethod
    def get_monthly_report(
        db: Session, year: Optional[int] = None, month: Optional[int] = None
    ) -> list[MonthlyReportRow]:
        """Total hours per employee for a given month (defaults to current month)."""
        today = datetime.now(timezone.utc).date()
        year = year or today.year
        month = month or today.month
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)

        sessions = (
            db.query(AttendanceSession, User)
            .join(User, AttendanceSession.user_id == User.id)
            .filter(
                AttendanceSession.login_date >= month_start,
                AttendanceSession.login_date < month_end,
                AttendanceSession.logout_time.isnot(None),
            )
            .all()
        )

        agg: dict[int, dict] = {}
        for s, u in sessions:
            if u.id not in agg:
                agg[u.id] = {
                    "name": u.name,
                    "department": str(u.department) if u.department else None,
                    "total_minutes": 0,
                    "session_count": 0,
                }
            agg[u.id]["total_minutes"] += s.duration_minutes or 0
            agg[u.id]["session_count"] += 1

        return [
            MonthlyReportRow(
                employee_id=uid,
                name=v["name"],
                department=v["department"],
                total_minutes=v["total_minutes"],
                total_hours=_fmt(v["total_minutes"]),
                session_count=v["session_count"],
            )
            for uid, v in sorted(agg.items(), key=lambda x: x[1]["name"])
        ]

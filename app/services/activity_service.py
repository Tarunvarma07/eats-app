"""
ActivityService — business logic for activity monitoring.
Sits between the router and repository layers.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceSession
from app.models.users import User
from app.repositories.activity_repository import ActivityRepository
from app.schemas.activity import (
    ActivityTodayRow,
    ActivityHistoryRow,
    ActivityWeeklyRow,
    ActivityMonthlyRow,
)

logger = logging.getLogger(__name__)


def _active_pct(active: int, idle: int) -> float:
    total = active + idle
    if total == 0:
        return 0.0
    return round(active / total * 100, 1)


def _fmt(minutes: int) -> str:
    return f"{minutes // 60}h {minutes % 60}m"


def _elapsed_minutes(login_time: datetime) -> int:
    now = datetime.now(timezone.utc)
    return max(0, int((now - login_time).total_seconds() / 60))


class ActivityService:

    # ── Employee write ────────────────────────────────────────────────────────

    @staticmethod
    def record_heartbeat(
        db: Session,
        user_id: int,
        status: str,
        idle_seconds: Optional[int],
    ) -> dict:
        """
        Validate that an open session exists, then insert an ActivityLog row.
        Raises ValueError (→ 409) if no open session.
        """
        session = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.user_id == user_id,
                AttendanceSession.logout_time.is_(None),
            )
            .first()
        )

        if session is None:
            logger.warning(f"Hebeat rejected for user {user_id}: no open session")
            raise ValueError(
                "No open attendance session — heartbeats are only accepted "
                "while you are clocked in."
            )

        ActivityRepository.insert_heartbeat(
            db=db,
            session_id=session.id,
            user_id=user_id,
            status=status,
            idle_seconds=idle_seconds,
        )
        return {"recorded": True, "session_id": session.id}

    @staticmethod
    def override_work_location(
        db: Session,
        user_id: int,
        work_location: str,
    ) -> dict:
        """
        Let the employee manually correct office/WFH for their current open session.
        Returns error string (→ 409) if no open session.
        """
        session = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.user_id == user_id,
                AttendanceSession.logout_time.is_(None),
            )
            .first()
        )

        if session is None:
            logger.warning(f"Work location override rejected for user {user_id}: no open session")
            raise ValueError(
                "No open session — work location can only be changed "
                "while you are clocked in."
            )

        session.work_location   = work_location
        session.location_source = "manual"
        db.commit()
        db.refresh(session)

        return {
            "updated": True,
            "session_id":      session.id,
            "work_location":   session.work_location,
            "location_source": session.location_source,
        }

    # ── Compute + cache at logout ─────────────────────────────────────────────

    @staticmethod
    def finalize_session_activity(db: Session, session: AttendanceSession) -> None:
        """
        Called by AuthService.logout_user — computes active/idle totals from
        ActivityLogs and caches them on the closed session.
        """
        active_min, idle_min = ActivityRepository.compute_active_idle(db, session.id)
        session.active_minutes = active_min
        session.idle_minutes   = idle_min
        db.commit()

    # ── Admin reads ───────────────────────────────────────────────────────────

    @staticmethod
    def get_today_activity(db: Session) -> list[ActivityTodayRow]:
        summaries = ActivityRepository.get_today_activity_summary(db)
        rows = []

        for item in summaries:
            s: AttendanceSession = item["session"]
            user = db.query(User).filter(User.id == s.user_id).first()
            if not user:
                continue

            active_min = item["active_minutes"]
            idle_min   = item["idle_minutes"]
            latest_hb  = item["latest_hb"]
            is_open    = s.logout_time is None

            rows.append(ActivityTodayRow(
                user_id=user.id,
                name=user.name,
                department=str(user.department) if user.department else None,
                work_location=s.work_location   or "unknown",
                location_source=s.location_source or "auto",
                login_time=s.login_time,
                logout_time=s.logout_time,
                total_logged_minutes=_elapsed_minutes(s.login_time) if is_open
                                     else (s.duration_minutes or 0),
                active_minutes=active_min,
                idle_minutes=idle_min,
                active_percent=_active_pct(active_min, idle_min),
                last_heartbeat=latest_hb.timestamp if latest_hb else None,
                heartbeat_status=latest_hb.status if latest_hb else None,
                session_status="Active" if is_open else "Logged Out",
            ))

        return rows

    @staticmethod
    def get_user_activity(db: Session, user_id: int) -> list[ActivityHistoryRow]:
        summaries = ActivityRepository.get_user_sessions_with_activity(db, user_id)
        rows = []

        for item in summaries:
            s: AttendanceSession = item["session"]
            active_min = item["active_minutes"]
            idle_min   = item["idle_minutes"]

            rows.append(ActivityHistoryRow(
                session_id=s.id,
                login_time=s.login_time,
                logout_time=s.logout_time,
                work_location=s.work_location   or "unknown",
                location_source=s.location_source or "auto",
                active_minutes=active_min,
                idle_minutes=idle_min,
                active_percent=_active_pct(active_min, idle_min),
                total_heartbeats=item["total_hb"],
            ))

        return rows

    @staticmethod
    def get_weekly_activity(db: Session) -> list[ActivityWeeklyRow]:
        from datetime import date as date_type
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())

        sessions = (
            db.query(AttendanceSession, User)
            .join(User, AttendanceSession.user_id == User.id)
            .filter(AttendanceSession.login_date >= week_start)
            .all()
        )

        agg: dict[int, dict] = {}
        for s, u in sessions:
            if u.id not in agg:
                agg[u.id] = {
                    "name": u.name,
                    "department": str(u.department) if u.department else None,
                    "total_minutes": 0,
                    "active_sum": 0,
                    "idle_sum": 0,
                    "office_days": 0,
                    "remote_days": 0,
                    "unknown_days": 0,
                }

            agg[u.id]["total_minutes"] += s.duration_minutes or 0

            if s.logout_time is None:
                am, im = ActivityRepository.compute_active_idle(db, s.id)
            else:
                am, im = s.active_minutes or 0, s.idle_minutes or 0

            agg[u.id]["active_sum"] += am
            agg[u.id]["idle_sum"]   += im

            loc = s.work_location or "unknown"
            if loc == "office":   agg[u.id]["office_days"]  += 1
            elif loc == "remote": agg[u.id]["remote_days"]  += 1
            else:                 agg[u.id]["unknown_days"] += 1

        return [
            ActivityWeeklyRow(
                employee_id=uid,
                name=v["name"],
                department=v["department"],
                total_hours=_fmt(v["total_minutes"]),
                avg_active_percent=_active_pct(v["active_sum"], v["idle_sum"]),
                office_days=v["office_days"],
                remote_days=v["remote_days"],
                unknown_days=v["unknown_days"],
            )
            for uid, v in sorted(agg.items(), key=lambda x: x[1]["name"])
        ]

    @staticmethod
    def get_monthly_activity(
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> list[ActivityMonthlyRow]:
        from datetime import date as date_type
        today = datetime.now(timezone.utc).date()
        year  = year  or today.year
        month = month or today.month

        from datetime import date
        month_start = date(year, month, 1)
        month_end   = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        sessions = (
            db.query(AttendanceSession, User)
            .join(User, AttendanceSession.user_id == User.id)
            .filter(
                AttendanceSession.login_date >= month_start,
                AttendanceSession.login_date <  month_end,
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
                    "active_sum": 0,
                    "idle_sum": 0,
                    "office_days": 0,
                    "remote_days": 0,
                    "unknown_days": 0,
                }

            agg[u.id]["total_minutes"] += s.duration_minutes or 0

            if s.logout_time is None:
                am, im = ActivityRepository.compute_active_idle(db, s.id)
            else:
                am, im = s.active_minutes or 0, s.idle_minutes or 0

            agg[u.id]["active_sum"] += am
            agg[u.id]["idle_sum"]   += im

            loc = s.work_location or "unknown"
            if loc == "office":   agg[u.id]["office_days"]  += 1
            elif loc == "remote": agg[u.id]["remote_days"]  += 1
            else:                 agg[u.id]["unknown_days"] += 1

        return [
            ActivityMonthlyRow(
                employee_id=uid,
                name=v["name"],
                department=v["department"],
                total_hours=_fmt(v["total_minutes"]),
                avg_active_percent=_active_pct(v["active_sum"], v["idle_sum"]),
                office_days=v["office_days"],
                remote_days=v["remote_days"],
                unknown_days=v["unknown_days"],
            )
            for uid, v in sorted(agg.items(), key=lambda x: x[1]["name"])
        ]

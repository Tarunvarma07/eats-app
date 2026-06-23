from datetime import datetime, timezone, time, date as DateType
from typing import Optional
import logging

import pytz
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attendance import AttendanceSession
from app.repositories.attendance_repository import (
    AttendanceRepository
)

from app.schemas.attendance import (
    AttendanceHistoryResponse
)

logger = logging.getLogger(__name__)


def _is_login_late(login_utc: datetime) -> bool:
    """
    Determine if a UTC login time is after the configured office
    start time in the office's local timezone (default: IST UTC+5:30).

    This is the critical fix for the UTC/IST late-login bug:
    9:30 AM IST = 04:00 AM UTC. Without this conversion, any employee
    logging in at 9:31 AM IST would NOT be flagged as late when
    comparing directly against UTC values.
    """
    office_tz = pytz.timezone(settings.OFFICE_TIMEZONE)
    login_local = login_utc.astimezone(office_tz)
    cutoff = time(
        settings.LATE_LOGIN_HOUR,
        settings.LATE_LOGIN_MINUTE
    )
    return login_local.time() > cutoff


class AttendanceService:

    @staticmethod
    def record_login(
        db: Session,
        user_id: int,
        ip_address: str | None = None,
        work_location: str = "unknown",
        location_source: str = "auto",
    ):

        active_session = (
            AttendanceRepository.get_active_session(
                db,
                user_id
            )
        )

        if active_session:
            # Auto-close the stale session (e.g. browser crash / tab close /
            # server restart left it open) so the user can log in again cleanly.
            now_close = datetime.now(timezone.utc)
            active_session.logout_time = now_close
            active_session.duration_minutes = int(
                (now_close - active_session.login_time).total_seconds() / 60
            )
            AttendanceRepository.update_session(db, active_session)

        now = datetime.now(timezone.utc)

        attendance = AttendanceSession(
            user_id=user_id,
            login_time=now,
            login_date=now.date(),
            ip_address=ip_address,
            is_late=_is_login_late(now),
            work_location=work_location,
            location_source=location_source,
        )

        return AttendanceRepository.create_session(
            db,
            attendance
        )


    @staticmethod
    def record_logout(
        db: Session,
        user_id: int
    ):

        active_session = (
            AttendanceRepository.get_active_session(
                db,
                user_id
            )
        )

        if not active_session:
            logger.warning(f"Logout attempted for user {user_id} with no active session")
            raise ValueError(
                "No active session found"
            )

        logout_time = datetime.now(
            timezone.utc
        )

        active_session.logout_time = logout_time

        duration = (
            logout_time -
            active_session.login_time
        )

        active_session.duration_minutes = int(
            duration.total_seconds() / 60
        )

        return AttendanceRepository.update_session(
            db,
            active_session
        )

    @staticmethod
    def format_duration(
        duration_minutes: int
    ) -> str:

        hours = duration_minutes // 60

        minutes = duration_minutes % 60

        return f"{hours}h {minutes}m"
    
    @staticmethod
    def get_attendance_history(
        db: Session,
        user_id: int,
        start_date: Optional[DateType] = None,
        end_date: Optional[DateType] = None
    ):

        sessions = (
            AttendanceRepository.get_user_sessions(
                db,
                user_id
            )
        )

        # Filter by date range if provided
        if start_date or end_date:
            sessions = [
                s for s in sessions
                if (not start_date or s.login_date >= start_date)
                and (not end_date or s.login_date <= end_date)
            ]

        history = []

        for session in sessions:

            if session.logout_time is None:

                duration = "Active"

            else:

                duration = (
                    AttendanceService.format_duration(
                        session.duration_minutes
                    )
                )

            history.append(
                AttendanceHistoryResponse(
                    session_id=session.id,
                    login_date=session.login_date,
                    login_time=session.login_time,
                    logout_time=session.logout_time,
                    duration=duration,
                    is_late=session.is_late
                )
            )

        return history
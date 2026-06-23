from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
import logging

from app.models.attendance import AttendanceSession

logger = logging.getLogger(__name__)


class AttendanceRepository:

    @staticmethod
    def create_session(
        db: Session,
        attendance: AttendanceSession
    ) -> AttendanceSession:
        try:
            db.add(attendance)
            db.commit()
            db.refresh(attendance)
            return attendance
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error creating attendance session: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to record attendance")

    @staticmethod
    def get_active_session(
        db: Session,
        user_id: int
    ) -> AttendanceSession | None:
        try:
            return (
                db.query(AttendanceSession)
                .filter(
                    AttendanceSession.user_id == user_id,
                    AttendanceSession.logout_time.is_(None)
                )
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching active session for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def update_session(
        db: Session,
        attendance: AttendanceSession
    ) -> AttendanceSession:
        try:
            db.commit()
            db.refresh(attendance)
            return attendance
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error updating attendance session: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update attendance")

    @staticmethod
    def get_user_sessions(
        db: Session,
        user_id: int
    ) -> list[AttendanceSession]:
        try:
            return (
                db.query(AttendanceSession)
                .filter(
                    AttendanceSession.user_id == user_id
                )
                .order_by(
                    AttendanceSession.login_time.desc()
                )
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching sessions for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def close_stale_sessions(
        db: Session,
        hours: int = 12
    ) -> int:
        """
        Close all sessions that are still open but whose login_time
        is older than `hours` hours. Called on server startup to handle
        sessions orphaned by a crash or unexpected shutdown.

        Sets logout_time = login_time + hours and duration_minutes = hours*60.
        Returns the number of sessions closed.
        """
        from datetime import datetime, timezone, timedelta

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            stale = (
                db.query(AttendanceSession)
                .filter(
                    AttendanceSession.logout_time.is_(None),
                    AttendanceSession.login_time < cutoff
                )
                .all()
            )

            for session in stale:
                synthetic_logout = session.login_time + timedelta(hours=hours)
                session.logout_time = synthetic_logout
                session.duration_minutes = hours * 60

            if stale:
                db.commit()

            return len(stale)
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error closing stale sessions: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to close stale sessions")

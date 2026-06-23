"""
ActivityRepository — raw DB queries for activity logs.
All business logic lives in ActivityService.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
import logging

from app.models.activity_log import ActivityLog
from app.models.attendance import AttendanceSession

logger = logging.getLogger(__name__)


class ActivityRepository:

    @staticmethod
    def insert_heartbeat(
        db: Session,
        session_id: int,
        user_id: int,
        status: str,
        idle_seconds: Optional[int],
    ) -> ActivityLog:
        try:
            log = ActivityLog(
                session_id=session_id,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
                status=status,
                idle_seconds=idle_seconds,
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error inserting heartbeat for session {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to record activity")

    @staticmethod
    def compute_active_idle(db: Session, session_id: int) -> tuple[int, int]:
        """
        Returns (active_minutes, idle_minutes) from raw ActivityLog rows
        for a given session.

        Strategy: count heartbeats by status, multiply by estimated interval (1.5 min).
        This is an approximation — precise minute-level accuracy requires
        storing interval durations, which would increase write volume.
        """
        try:
            HEARTBEAT_INTERVAL_MINUTES = 1.5   # matches agent default (90 s)

            rows = db.query(ActivityLog.status, func.count(ActivityLog.id)) \
                     .filter(ActivityLog.session_id == session_id) \
                     .group_by(ActivityLog.status) \
                     .all()

            counts = {row[0]: row[1] for row in rows}
            active_min = int(counts.get("active", 0) * HEARTBEAT_INTERVAL_MINUTES)
            idle_min   = int(counts.get("idle",   0) * HEARTBEAT_INTERVAL_MINUTES)
            return active_min, idle_min
        except SQLAlchemyError as e:
            logger.error(f"DB error computing activity for session {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def get_session_heartbeats(db: Session, session_id: int) -> list[ActivityLog]:
        try:
            return (
                db.query(ActivityLog)
                .filter(ActivityLog.session_id == session_id)
                .order_by(ActivityLog.timestamp.desc())
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching heartbeats for session {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def get_latest_heartbeat(db: Session, session_id: int) -> Optional[ActivityLog]:
        try:
            return (
                db.query(ActivityLog)
                .filter(ActivityLog.session_id == session_id)
                .order_by(ActivityLog.timestamp.desc())
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching latest heartbeat for session {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def get_today_activity_summary(db: Session) -> list[dict]:
        """
        Returns one dict per open/closed session today with pre-computed
        active/idle/heartbeat counts — used by GET /admin/activity/today.
        """
        try:
            today = datetime.now(timezone.utc).date()

            sessions = (
                db.query(AttendanceSession)
                .filter(AttendanceSession.login_date == today)
                .all()
            )

            results = []
            for s in sessions:
                # For closed sessions: use cached columns; for open: compute live
                if s.logout_time is None:
                    active_min, idle_min = ActivityRepository.compute_active_idle(db, s.id)
                else:
                    active_min = s.active_minutes or 0
                    idle_min   = s.idle_minutes   or 0

                latest_hb = ActivityRepository.get_latest_heartbeat(db, s.id)
                total_hb  = db.query(func.count(ActivityLog.id)) \
                              .filter(ActivityLog.session_id == s.id).scalar() or 0

                results.append({
                    "session":        s,
                    "active_minutes": active_min,
                    "idle_minutes":   idle_min,
                    "total_hb":       total_hb,
                    "latest_hb":      latest_hb,
                })

            return results
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching today's activity summary: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def get_user_sessions_with_activity(db: Session, user_id: int) -> list[dict]:
        """All sessions for one user, with activity summary per session."""
        try:
            sessions = (
                db.query(AttendanceSession)
                .filter(AttendanceSession.user_id == user_id)
                .order_by(AttendanceSession.login_time.desc())
                .all()
            )

            results = []
            for s in sessions:
                if s.logout_time is None:
                    active_min, idle_min = ActivityRepository.compute_active_idle(db, s.id)
                else:
                    active_min = s.active_minutes or 0
                    idle_min   = s.idle_minutes   or 0

                total_hb = db.query(func.count(ActivityLog.id)) \
                             .filter(ActivityLog.session_id == s.id).scalar() or 0

                results.append({
                    "session":        s,
                    "active_minutes": active_min,
                    "idle_minutes":   idle_min,
                    "total_hb":       total_hb,
                })

            return results
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching sessions for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

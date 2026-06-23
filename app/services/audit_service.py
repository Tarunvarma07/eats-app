from sqlalchemy.orm import Session
import logging

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Write-only audit logging service.
    Call AuditService.log() on any significant state-changing operation.
    """

    @staticmethod
    def log(
        db: Session,
        action: str,
        entity: str,
        user_id: int | None = None,
        entity_id: int | None = None,
        detail: dict | None = None
    ) -> None:
        """
        Record an audit event.

        Args:
            db:        SQLAlchemy session
            action:    Short uppercase verb, e.g. "LOGIN", "REGISTER", "LOGOUT"
            entity:    Table/domain name, e.g. "user", "attendance_session"
            user_id:   ID of the acting user (None for system events)
            entity_id: PK of the affected row (None for non-specific actions)
            detail:    Optional dict with extra context (IP, email, etc.)
        """
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                detail=detail
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event {action} on {entity}: {e}", exc_info=True)
            # Don't raise - audit logging failure shouldn't break the main operation

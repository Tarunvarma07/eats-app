from datetime import datetime, timezone
from sqlalchemy.orm import Session
import logging

from app.models.users import User
from app.schemas.users import UserCreate, UserLogin
from app.repositories.user_repository import UserRepository
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.core.token_blacklist import add_to_blacklist
from app.services.attendance_service import (
    AttendanceService
)
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def register_user(
        db: Session,
        user_data: UserCreate,
        role: str = "employee"
    ):

        existing_user = (
            UserRepository.get_user_by_email(
                db,
                user_data.email
            )
        )

        if existing_user:
            logger.warning(f"Registration attempt with existing email: {user_data.email}")
            raise ValueError(
                "Email already registered"
            )

        # Admin accounts are auto-approved, regular employees need approval
        is_approved = (role == "admin")

        user = User(
            name=user_data.name,
            email=user_data.email,
            hashed_password=hash_password(
                user_data.password
            ),
            department=user_data.department,
            role=role,
            is_approved=is_approved
        )

        created = UserRepository.create_user(
            db,
            user
        )

        AuditService.log(
            db=db,
            action="REGISTER",
            entity="user",
            user_id=created.id,
            entity_id=created.id,
            detail={
                "email": user_data.email,
                "department": str(user_data.department)
            }
        )

        return created

    @staticmethod
    def login_user(
        db: Session,
        login_data: UserLogin,
        client_ip: str | None = None,
    ):
        from app.core.office_detection import classify_work_location

        user = (
            UserRepository.get_user_by_email(
                db,
                login_data.email
            )
        )

        if not user:
            logger.warning(f"Login attempt with non-existent email: {login_data.email}")
            raise ValueError(
                "Invalid credentials"
            )

        if not verify_password(
            login_data.password,
            user.hashed_password
        ):
            logger.warning(f"Failed login attempt for email: {login_data.email}")
            raise ValueError(
                "Invalid credentials"
            )

        if not user.is_approved:
            logger.warning(f"Login attempt by unapproved user: {login_data.email}")
            raise ValueError(
                "Your account is pending admin approval"
            )

        # Classify office vs remote via IP before creating the session
        work_location, location_source = classify_work_location(client_ip)

        session = AttendanceService.record_login(
            db=db,
            user_id=user.id,
            ip_address=client_ip,
            work_location=work_location,
            location_source=location_source,
        )

        access_token = (
            create_access_token(
                {
                    "user_id":    user.id,
                    "role":       user.role,
                    "name":       user.name,
                    "email":      user.email,
                    "department": str(user.department) if user.department else None,
                }
            )
        )

        AuditService.log(
            db=db,
            action="LOGIN",
            entity="user",
            user_id=user.id,
            entity_id=user.id,
            detail={"email": user.email}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    @staticmethod
    def logout_user(
        db: Session,
        user_id: int,
        token: str
    ):
        # Decode the token to extract JTI + expiry, then persist to DB blacklist.
        # Using DB-backed blacklist so revocation survives server restarts
        # and is visible to all Uvicorn worker processes.
        payload = decode_access_token(token)
        if payload and payload.get("jti"):
            exp_ts = payload.get("exp")
            expires_at = (
                datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                if exp_ts else None
            )
            add_to_blacklist(payload["jti"], expires_at=expires_at)

        # Finalize activity totals on the closing session
        from app.models.attendance import AttendanceSession
        from app.services.activity_service import ActivityService
        closing = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.user_id == user_id,
                AttendanceSession.logout_time.is_(None),
            )
            .first()
        )
        if closing:
            ActivityService.finalize_session_activity(db, closing)

        AttendanceService.record_logout(
            db=db,
            user_id=user_id
        )

        AuditService.log(
            db=db,
            action="LOGOUT",
            entity="user",
            user_id=user_id,
            entity_id=user_id
        )

        return {
            "message": "Logout successful"
        }

    @staticmethod
    def authenticate_user(
        db: Session,
        login_data: UserLogin
    ):
        user = UserRepository.get_user_by_email(
            db,
            login_data.email
        )

        if not user or not verify_password(
            login_data.password,
            user.hashed_password
        ):
            raise ValueError("Invalid credentials")

        return user

    @staticmethod
    def change_password(
        db: Session,
        user_id: int,
        current_password: str,
        new_password: str
    ):
        user = UserRepository.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")
        
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        
        user.hashed_password = hash_password(new_password)
        db.commit()
        db.refresh(user)
        
        AuditService.log(
            db=db,
            action="PASSWORD_CHANGE",
            entity="user",
            user_id=user_id,
            entity_id=user_id,
            detail={"email": user.email}
        )
        
        return user
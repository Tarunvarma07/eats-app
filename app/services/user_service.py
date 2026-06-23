from sqlalchemy.orm import Session
import logging

from app.repositories.user_repository import (
    UserRepository
)

from app.schemas.users import (
    AdminUserResponse
)

from app.models.users import User

logger = logging.getLogger(__name__)


class UserService:

    @staticmethod
    def get_all_users(
        db: Session,
        skip: int = 0,
        limit: int = 50
    ):

        users = (
            UserRepository.get_all_users(
                db,
                skip=skip,
                limit=limit
            )
        )

        return [
            AdminUserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                department=user.department,
                is_active=user.is_active,
                is_approved=user.is_approved,
                created_at=user.created_at
            )
            for user in users
        ]

    @staticmethod
    def count_users(db: Session) -> int:
        """Count total number of users."""
        return db.query(User).count()

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        **kwargs
    ):
        user = UserRepository.update_user(db, user_id, **kwargs)
        return AdminUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            department=user.department,
            is_active=user.is_active,
            is_approved=user.is_approved,
            created_at=user.created_at
        )

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        return UserRepository.delete_user(db, user_id)
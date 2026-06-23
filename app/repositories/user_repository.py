from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
import logging

from app.models.users import User

logger = logging.getLogger(__name__)


class UserRepository:

    @staticmethod
    def create_user(
        db: Session,
        user: User
    ) -> User:
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error creating user: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create user")

    @staticmethod
    def get_user_by_email(
        db: Session,
        email: str
    ) -> User | None:
        try:
            return (
                db.query(User)
                .filter(User.email == email)
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching user by email {email}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def get_user_by_id(
        db: Session,
        user_id: int
    ) -> User | None:
        try:
            return (
                db.query(User)
                .filter(User.id == user_id)
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def get_all_users(
        db: Session,
        skip: int = 0,
        limit: int = 50
    ):
        try:
            return (
                db.query(User)
                .order_by(
                    User.created_at.desc()
                )
                .offset(skip)
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching users: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        **kwargs
    ) -> User:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            for key, value in kwargs.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            db.commit()
            db.refresh(user)
            return user
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error updating user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update user")

    @staticmethod
    def delete_user(
        db: Session,
        user_id: int
    ) -> bool:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            db.delete(user)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error deleting user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete user")
from typing import Optional
from math import ceil

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.core.dependencies import require_admin
from app.schemas.users import AdminUserResponse
from app.schemas.attendance import (
    AdminAttendanceRow,
    DashboardStats,
    WeeklyReportRow,
    MonthlyReportRow,
)
from app.services.user_service import UserService
from app.services.admin_service import AdminService


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserCreateRequest(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


router = APIRouter(
    tags=["Admin"],
)


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    summary="List all employees (paginated)",
)
@router.get(
    "/employees",
    summary="List all employees — SRS alias for /admin/users",
    include_in_schema=True,
)
def get_all_users(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    total = UserService.count_users(db)
    users = UserService.get_all_users(db, skip=(page - 1) * page_size, limit=page_size)
    return {
        "data": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size),
    }


@router.post(
    "/users",
    summary="Create a new user (admin only)",
    status_code=201,
)
def create_user(
    user_data: UserCreateRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.user_service import UserService
    from app.core.security import hash_password
    
    # Set default password if not provided
    if not user_data.password:
        # Generate a random default password
        import secrets
        default_password = secrets.token_urlsafe(12)
        hashed = hash_password(default_password)
    else:
        hashed = hash_password(user_data.password)
    
    from app.models.users import User
    user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed,
        role=user_data.role if user_data.role else "employee",
        department=user_data.department,
        is_active=user_data.is_active if user_data.is_active is not None else True,
        is_approved=True,  # Admin-created users are auto-approved
    )
    
    created = UserService.create_user(db, user)
    return created


@router.put(
    "/users/{user_id}",
    summary="Update a user (admin only)",
)
def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    update_data = user_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    return UserService.update_user(db, user_id, **update_data)


@router.delete(
    "/users/{user_id}",
    summary="Delete a user (admin only)",
)
def delete_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    UserService.delete_user(db, user_id)
    return {"message": "User deleted successfully"}


@router.post(
    "/users/{user_id}/approve",
    summary="Approve a pending user registration (admin only)",
)
def approve_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    UserService.update_user(db, user_id, is_approved=True)
    return {"message": "User approved successfully"}


@router.get(
    "/users/pending",
    summary="List pending user registrations (admin only)",
)
def get_pending_users(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.models.users import User
    from app.repositories.user_repository import UserRepository
    pending = (
        db.query(User)
        .filter(User.is_approved == False, User.is_active == True)
        .order_by(User.created_at.desc())
        .all()
    )
    return [
        AdminUserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role,
            department=u.department,
            is_active=u.is_active,
            is_approved=u.is_approved,
            created_at=u.created_at
        )
        for u in pending
    ]


# ---------------------------------------------------------------------------
# Dashboard stats card  (FR-21)
# ---------------------------------------------------------------------------

@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Summary stat cards: total employees, logged-in, late today, avg hours",
)
def get_dashboard_stats(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminService.get_dashboard_stats(db)


# ---------------------------------------------------------------------------
# Today's attendance  (FR-12, UC-03)
# ---------------------------------------------------------------------------

@router.get(
    "/attendance/today",
    response_model=list[AdminAttendanceRow],
    summary="All employees' sessions for today (FR-12)",
)
def get_today_attendance(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    department: Optional[str] = None,
    status: Optional[str] = None,
):
    return AdminService.get_today_attendance(db, department=department, status=status)


# ---------------------------------------------------------------------------
# Per-employee session history  (FR-17)
# ---------------------------------------------------------------------------

@router.get(
    "/attendance/{user_id}",
    response_model=list[AdminAttendanceRow],
    summary="Full session history for one employee (FR-17)",
)
def get_employee_history(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminService.get_employee_history(db, user_id)


# ---------------------------------------------------------------------------
# Reports  (FR-18, FR-19)
# ---------------------------------------------------------------------------

@router.get(
    "/report/weekly",
    response_model=list[WeeklyReportRow],
    summary="Total hours per employee for the current week (FR-18)",
)
def get_weekly_report(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminService.get_weekly_report(db)


@router.get(
    "/report/monthly",
    response_model=list[MonthlyReportRow],
    summary="Total hours per employee for a given month (FR-19)",
)
def get_monthly_report(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminService.get_monthly_report(db, year=year, month=month)
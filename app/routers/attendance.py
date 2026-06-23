from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)
from datetime import date as DateType
from typing import Optional
from math import ceil

from sqlalchemy.orm import Session

from app.db.database import get_db

from app.core.dependencies import (
    get_current_user
)

from app.schemas.attendance import (
    AttendanceHistoryResponse
)
from app.schemas.activity import WorkLocationOverride

from app.services.attendance_service import (
    AttendanceService
)
from app.services.activity_service import ActivityService


router = APIRouter(
    tags=["Attendance"]
)


@router.get(
    "/me",
    summary="Get current user's attendance history (paginated)"
)
def get_my_attendance(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[DateType] = None,
    end_date: Optional[DateType] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    records = AttendanceService.get_attendance_history(
        db=db,
        user_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date
    )

    total = len(records)
    paginated_records = records[(page - 1) * page_size:page * page_size]

    return {
        "data": paginated_records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size),
    }


@router.post(
    "/clock-in",
    summary="Employee clocks in - starts a new attendance session",
)
def clock_in(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.office_detection import get_client_ip
    try:
        return AttendanceService.record_login(
            db=db,
            user_id=current_user["user_id"],
            ip_address=get_client_ip(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post(
    "/clock-out",
    summary="Employee clocks out - ends current attendance session",
)
def clock_out(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return AttendanceService.record_logout(
            db=db,
            user_id=current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post(
    "/work-location",
    summary="Employee corrects their own session's office/WFH classification",
)
def override_work_location(
    body: WorkLocationOverride,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates work_location to 'office' or 'remote' and sets location_source='manual'.
    Only applies to the calling employee's current OPEN session.
    Returns 409 if no open session exists.
    """
    try:
        return ActivityService.override_work_location(
            db=db,
            user_id=current_user["user_id"],
            work_location=body.work_location,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
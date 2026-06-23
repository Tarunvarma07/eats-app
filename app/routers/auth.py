from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    Cookie
)
from pydantic import ValidationError, BaseModel
from jose import JWTError
from app.core.dependencies import (
    get_current_user
)

from fastapi.security import (
    OAuth2PasswordRequestForm
)

from slowapi import Limiter
from slowapi.util import get_remote_address

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.users import (
    UserCreate,
    UserLogin,
    UserResponse
)
from pydantic import BaseModel


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


from app.services.auth_service import AuthService
from app.models.users import User
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token
)


limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new employee account"
)
@limiter.limit("3/minute")
def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):

    try:

        return AuthService.register_user(
            db,
            user_data
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post(
    "/admin-setup",
    response_model=UserResponse,
    status_code=201,
    summary="One-time admin account creation — only works when no admin exists yet"
)
def admin_setup(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Bootstrap the first admin (CFO/CEO) account.
    Once any admin exists this endpoint permanently returns 403.
    No auth required — intended for first-run setup only.
    """
    existing_admin = db.query(User).filter(User.role == "admin").first()
    if existing_admin:
        raise HTTPException(
            status_code=403,
            detail="An admin account already exists. Contact your system administrator."
        )

    try:
        return AuthService.register_user(db, user_data, role="admin")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    from app.core.office_detection import get_client_ip

    try:
        result = AuthService.login_user(
            db,
            login_data,
            client_ip=get_client_ip(request),
        )

        # Generate refresh token and set as httpOnly cookie
        refresh_token = create_refresh_token(data={"sub": login_data.email})
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",  # Changed from strict to lax for cross-site redirects
            max_age=7 * 24 * 3600  # 7 days in seconds
        )

        return result

    except ValueError as e:

        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )



@router.post("/token")
@limiter.limit("5/minute")
def get_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    try:

        login_data = UserLogin(
            email=form_data.username,
            password=form_data.password
        )

        return AuthService.login_user(
            db,
            login_data
        )

    except (ValueError, ValidationError) as e:

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials — enter your registered email as the username.",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):
    # Extract the raw token from the Authorization header so we can
    # blacklist its JTI for immediate revocation.
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()

    try:

        result = AuthService.logout_user(
            db=db,
            user_id=current_user["user_id"],
            token=token
        )

        # Clear refresh token cookie
        response.delete_cookie("refresh_token")

        return result

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post("/refresh")
def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    try:
        payload = verify_refresh_token(refresh_token)
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Verify user still exists and is active
    from app.repositories.user_repository import UserRepository
    user = UserRepository.get_user_by_email(db, email)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Issue new access token
    new_access_token = create_access_token(data={"sub": email})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.services.auth_service import AuthService
    try:
        AuthService.change_password(
            db=db,
            user_id=current_user["user_id"],
            current_password=body.current_password,
            new_password=body.new_password
        )
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.repositories.user_repository import UserRepository
    user = UserRepository.get_user_by_id(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "department": user.department,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at
    }
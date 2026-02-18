from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST

from ..core.security import create_access_token, hash_password, verify_password
from ..db.models import User
from ..db.session import get_db
from ..deps import get_current_user
from ..schemas import AuthLoginRequest, AuthRegisterRequest, AuthResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    summary="Register",
    description="Register a new user and return a JWT token.",
    operation_id="register",
)
async def register(payload: AuthRegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Register a user (email + password)."""
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"user_id": user.id, "email": user.email})
    return AuthResponse(
        token=token, user=UserOut(id=user.id, email=user.email, created_at=user.created_at)
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login",
    description="Login with email/password and return a JWT token.",
    operation_id="login",
)
async def login(payload: AuthLoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Login (email + password)."""
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    token = create_access_token({"user_id": user.id, "email": user.email})
    return AuthResponse(
        token=token, user=UserOut(id=user.id, email=user.email, created_at=user.created_at)
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
    description="Return the current authenticated user.",
    operation_id="get_me",
)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    """Return current user."""
    return UserOut(id=user.id, email=user.email, created_at=user.created_at)

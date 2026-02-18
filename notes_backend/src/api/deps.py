from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED

from .core.security import decode_access_token
from .db.models import User
from .db.session import get_db

bearer = HTTPBearer(auto_error=False)


# PUBLIC_INTERFACE
async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the currently authenticated user from Authorization: Bearer <token>."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_access_token(creds.credentials)
        subject = payload.get("sub") or {}
        user_id = subject.get("user_id")
        if not user_id:
            raise ValueError("missing user_id")
    except Exception:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

    res = await db.execute(select(User).where(User.id == int(user_id)))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

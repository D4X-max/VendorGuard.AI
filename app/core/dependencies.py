from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_tenant_session
from app.core.config import settings
bearer_scheme = HTTPBearer()


class AuthenticatedUser:
    """Carries decoded JWT claims for the current request."""
    def __init__(self, user_id: str, tenant_id: str, email: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """
    Validates the Bearer JWT token on every protected route.
    Extracts user_id and tenant_id from token claims.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)

        if payload.get("type") != "access":
            raise credentials_exception

        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tid")
        email: str = payload.get("email", "")

        if not user_id or not tenant_id:
            raise credentials_exception

        return AuthenticatedUser(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
        )
    except JWTError:
        raise credentials_exception


async def get_db(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a tenant-scoped DB session for repository use.
    RLS context is injected automatically using the tenant_id
    extracted from the JWT token.
    """
    async for session in get_tenant_session(current_user.tenant_id):
        yield session
from typing import List, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.database import async_session_maker
from app.domain.schemas.user import UserInDB
from app.models.all_models import User, Role
from sqlalchemy import select
from sqlalchemy.orm import selectinload

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserInDB:
    """
    Validates Bearer JWT. Extracts user_id + tenant_id.
    Loads user's permissions from DB for RBAC checks.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise exc
        user_id = payload.get("sub")
        tenant_id = payload.get("tid") or payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise exc
    except JWTError:
        raise exc

    # Load user + roles + permissions from DB
    async with async_session_maker() as session:
        result = await session.execute(
            select(User)
            .where(User.id == user_id, User.is_active == True)
            .options(
                selectinload(User.roles).selectinload(Role.permissions)
            )
        )
        user = result.scalar_one_or_none()

    if not user:
        raise exc

    # Flatten permissions from all roles
    permissions = []
    for role in user.roles:
        for perm in role.permissions:
            permissions.append(perm.code)

    return UserInDB(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        permissions=permissions,
    )


def require_permissions(required: List[str]) -> Callable:
    """
    RBAC guard. Usage: Depends(require_permissions(["vendor:write"]))
    Returns the user if they have ALL required permissions.
    """
    async def permission_checker(
        current_user: UserInDB = Depends(get_current_user),
    ) -> UserInDB:
        for perm in required:
            if perm not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: '{perm}'",
                )
        return current_user

    return permission_checker


# Convenience alias — use on routes that just need auth, no specific permission
get_current_active_user = get_current_user
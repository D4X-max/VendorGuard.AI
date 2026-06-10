from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.api.dependencies.auth import get_current_active_user
from app.domain.schemas.user import (
    TenantRegisterRequest, LoginRequest, TokenResponse, UserResponse, UserInDB
)
from app.domain.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: TenantRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthService(session)
    return await service.register_tenant(body)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthService(session)
    return await service.login(body, response)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    from app.core.security import decode_token
    from jose import JWTError
    from fastapi import HTTPException
    from app.core.security import create_access_token
    from app.core.config import settings

    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing.")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type.")
        access_token = create_access_token(
            subject=payload["sub"],
            tenant_id=payload["tid"],
            role=payload.get("role", "user"),
        )
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_active_user)):
    return current_user
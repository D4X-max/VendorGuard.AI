from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.schemas import (
    LoginRequest, TokenResponse, RefreshRequest, TenantRegisterRequest, UserResponse
)
from app.repositories.repositories import TenantRepository, UserRepository
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user, AuthenticatedUser
from app.db.session import get_system_session, get_tenant_session
from app.config import settings
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    request: Request,
    body: TenantRegisterRequest,
):
    """
    Provisions a new tenant + admin user in a single atomic transaction.
    Used for onboarding new organizations onto VendorGuard.AI.
    """
    async for session in get_system_session():
        # Check domain uniqueness
        existing = await TenantRepository.get_by_domain(session, body.tenant_domain)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Domain '{body.tenant_domain}' is already registered.",
            )

        # Create tenant
        tenant = await TenantRepository.create(
            session, name=body.tenant_name, domain=body.tenant_domain
        )

        # Create admin user
        user = await UserRepository.create(
            session,
            tenant_id=tenant.id,
            email=body.admin_email,
            password=body.admin_password,
            first_name=body.admin_first_name,
            last_name=body.admin_last_name,
        )

        return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
):
    """
    Authenticates a user and returns JWT access + refresh tokens.
    The tenant_id is embedded in the token to power RLS on every request.
    """
    # We need the tenant domain from the email or a separate field.
    # For simplicity, we scan all tenants. In production, pass tenant domain in request.
    async for session in get_system_session():
        from sqlalchemy import select
        from app.models.all_models import User, Tenant

        # Find user by email across all tenants (for multi-tenant login page)
        result = await session.execute(
            select(User).where(User.email == body.email, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        access_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            extra_claims={"email": user.email},
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    """
    Issues a new access token using a valid refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception

        user_id = payload.get("sub")
        tenant_id = payload.get("tid")

        if not user_id or not tenant_id:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    access_token = create_access_token(subject=user_id, tenant_id=tenant_id)
    new_refresh_token = create_refresh_token(subject=user_id, tenant_id=tenant_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Returns the current authenticated user's profile from the JWT claims."""
    async for session in get_tenant_session(current_user.tenant_id):
        user = await UserRepository.get_by_id(session, current_user.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return UserResponse.model_validate(user)
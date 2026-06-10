import logging
from datetime import timedelta
from fastapi import HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.domain.repositories.user_repo import UserRepository, TenantRepository
from app.domain.schemas.user import LoginRequest, TokenResponse, TenantRegisterRequest, UserResponse
from app.models.all_models import User, Tenant

logger = logging.getLogger(__name__)


class AuthService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.tenant_repo = TenantRepository(session)

    async def register_tenant(self, body: TenantRegisterRequest) -> UserResponse:
        existing = await self.tenant_repo.get_by_domain(body.tenant_domain)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Domain '{body.tenant_domain}' is already registered.",
            )

        tenant = Tenant(name=body.tenant_name, domain=body.tenant_domain)
        await self.tenant_repo.create(tenant)

        admin = User(
            tenant_id=tenant.id,
            email=body.admin_email,
            password_hash=get_password_hash(body.admin_password),
            first_name=body.admin_first_name,
            last_name=body.admin_last_name,
        )
        await self.user_repo.create(admin)
        await self.session.commit()
        await self.session.refresh(admin)

        logger.info("New tenant registered", extra={"tenant_id": str(tenant.id)})
        return UserResponse.model_validate(admin)

    async def login(
        self, body: LoginRequest, response: Response
    ) -> TokenResponse:
        user = await self.user_repo.get_by_email(body.email)

        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )

        access_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            role="admin",
        )

        # HttpOnly refresh token — XSS cannot read this cookie
        from app.core.security import create_refresh_token
        refresh_token = create_refresh_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=not settings.is_development,
            samesite="strict",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            path="/api/v1/auth/refresh",
        )

        logger.info("User logged in", extra={"user_id": str(user.id)})
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
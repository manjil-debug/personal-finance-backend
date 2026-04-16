from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import AuthProvider, User
from app.schemas.user import LoginRequest, RefreshRequest, SignupRequest, TokenResponse


class AuthService:

    @staticmethod
    async def signup(payload: SignupRequest, db: AsyncSession) -> User:
        result = await db.execute(select(User).filter(User.email == payload.email))
        existing = result.scalar_one_or_none()
        if existing:
            raise ConflictException("An account with this email already exists")

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            provider=AuthProvider.local,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def login(payload: LoginRequest, db: AsyncSession) -> TokenResponse:
        result = await db.execute(select(User).filter(User.email == payload.email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise ForbiddenException("Account is deactivated")

        access_token = create_access_token(subject=str(user.id))
        raw_refresh, hashed_refresh = create_refresh_token()

        db_token = RefreshToken(
            user_id=user.id,
            token_hash=hashed_refresh,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(db_token)
        await db.commit()

        return TokenResponse(access_token=access_token, refresh_token=raw_refresh)

    @staticmethod
    async def refresh(payload: RefreshRequest, db: AsyncSession) -> TokenResponse:
        token_hash = hash_refresh_token(payload.refresh_token)
        result = await db.execute(
            select(RefreshToken).filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        db_token = result.scalar_one_or_none()

        if not db_token or db_token.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException("Invalid or expired refresh token")

        # Revoke old token
        db_token.revoked_at = datetime.now(timezone.utc)

        # Verify user is still active
        user_result = await db.execute(select(User).filter(User.id == db_token.user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            await db.commit()
            raise UnauthorizedException("User not found or inactive")

        # Issue new token pair
        access_token = create_access_token(subject=str(user.id))
        raw_refresh, hashed_refresh = create_refresh_token()

        new_db_token = RefreshToken(
            user_id=user.id,
            token_hash=hashed_refresh,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(new_db_token)
        await db.commit()

        return TokenResponse(access_token=access_token, refresh_token=raw_refresh)

    @staticmethod
    async def logout(payload: RefreshRequest, db: AsyncSession) -> None:
        token_hash = hash_refresh_token(payload.refresh_token)
        result = await db.execute(
            select(RefreshToken).filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.revoked_at = datetime.now(timezone.utc)
            await db.commit()

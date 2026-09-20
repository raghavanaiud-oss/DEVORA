import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.app.models.user import RefreshToken, User
from backend.app.repositories.user_repo import UserRepository
from backend.app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, user_in: UserCreate) -> TokenResponse:
        # Check existing email
        existing_email = await self.user_repo.get_by_email(user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "EMAIL_ALREADY_EXISTS", "message": "A user with this email already exists."}},
            )

        # Check existing username
        existing_username = await self.user_repo.get_by_username(user_in.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "USERNAME_ALREADY_EXISTS", "message": "This username is already taken."}},
            )

        user = User(
            email=user_in.email.lower(),
            username=user_in.username,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name or user_in.username,
            avatar_url=user_in.avatar_url or f"https://api.dicebear.com/7.x/identicon/svg?seed={user_in.username}",
        )
        created_user = await self.user_repo.create(user)

        access_token = create_access_token(subject=str(created_user.id))
        refresh_token_str = create_refresh_token(subject=str(created_user.id))

        refresh_token_obj = RefreshToken(
            user_id=created_user.id,
            token=refresh_token_str,
            expires_at=datetime.now(timezone.utc),
        )
        await self.user_repo.create_refresh_token(refresh_token_obj)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user=UserResponse.model_validate(created_user),
        )

    async def login(self, user_login: UserLogin) -> TokenResponse:
        user = await self.user_repo.get_by_email(user_login.email)
        if not user or not verify_password(user_login.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."}},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "USER_INACTIVE", "message": "User account has been deactivated."}},
            )

        access_token = create_access_token(subject=str(user.id))
        refresh_token_str = create_refresh_token(subject=str(user.id))

        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.now(timezone.utc),
        )
        await self.user_repo.create_refresh_token(refresh_token_obj)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user=UserResponse.model_validate(user),
        )

    async def refresh_tokens(self, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "INVALID_REFRESH_TOKEN", "message": "Invalid or expired refresh token."}},
            )

        token_obj = await self.user_repo.get_refresh_token(refresh_token_str)
        if not token_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "REVOKED_REFRESH_TOKEN", "message": "Refresh token has been revoked."}},
            )

        # Revoke previous refresh token (rotation)
        await self.user_repo.revoke_refresh_token(token_obj)

        user_id = uuid.UUID(payload["sub"])
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found or inactive."}},
            )

        new_access_token = create_access_token(subject=str(user.id))
        new_refresh_token_str = create_refresh_token(subject=str(user.id))

        new_refresh_token_obj = RefreshToken(
            user_id=user.id,
            token=new_refresh_token_str,
            expires_at=datetime.now(timezone.utc),
        )
        await self.user_repo.create_refresh_token(new_refresh_token_obj)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token_str,
            user=UserResponse.model_validate(user),
        )

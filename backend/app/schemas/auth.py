from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    display_name: str
    locale: str = Field(default="vi-VN")


class RegisterResponse(BaseModel):
    user_id: int
    requires_email_verification: bool = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserPublic"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    avatar_url: Optional[str] = None
    locale: str
    is_email_verified: bool


class UserUpdate(BaseModel):
    display_name: Optional[str]
    avatar_url: Optional[str]
    locale: Optional[str]


class UserStats(BaseModel):
    total_minutes: int = 0
    badges: int = 0
    quests_completed: int = 0


class UserProfile(UserPublic):
    stats: UserStats
    preferences: dict


class UserHistoryItem(BaseModel):
    session_id: int
    agent_id: str
    topic: str | None
    duration_minutes: int
    updated_at: datetime


class UserHistoryResponse(BaseModel):
    cursor: str | None = None
    items: list[UserHistoryItem]


UserPublic.model_rebuild()
TokenResponse.model_rebuild()

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Column, DateTime, Field, SQLModel, TEXT


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=False), nullable=False),
    )


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    display_name: str
    locale: str = "vi-VN"
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_email_verified: bool = False
    role: str = "user"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RefreshToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    jti: str = Field(index=True, unique=True)
    expires_at: datetime
    revoked: bool = Field(default=False)


class TimelineNode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    year_range: str
    agent_id: str
    summary: str
    color: str = "#4b5563"


class LibraryTopic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    period: str
    topic_type: str = Field(default="event")
    tags: str = Field(default="")
    markdown: str = Field(sa_column=Column(TEXT))
    agent_id: str = Field(default="agent_general_search")


class LibraryDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="librarytopic.id")
    source: str
    period: str
    content: str = Field(sa_column=Column(TEXT))


class ChatSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    agent_id: str
    hero_name: str = Field(default="Cố vấn lịch sử")  # Tên anh hùng/nhân vật lịch sử
    topic: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)


class SessionMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id")
    role: str
    content: str = Field(sa_column=Column(TEXT))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Quest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    title: str
    description: str
    category: str = Field(default="daily")
    reward_badge: Optional[str] = None


class UserQuest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quest_id: int = Field(foreign_key="quest.id")
    user_id: int = Field(foreign_key="user.id")
    status: str = Field(default="locked")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Badge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    title: str
    description: str


class UserBadge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    badge_id: int = Field(foreign_key="badge.id")
    user_id: int = Field(foreign_key="user.id")
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    body: str
    category: str = "system"


class UserNotification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    notification_id: int = Field(foreign_key="notification.id")
    user_id: int = Field(foreign_key="user.id")
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Memory(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")
    agent_id: str
    topic: str
    session_id: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

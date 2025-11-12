from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class QuestOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    category: str
    reward_badge: Optional[str]
    status: str


class QuestListResponse(BaseModel):
    quests: List[QuestOut]


class QuestProgressRequest(BaseModel):
    status: str
    evidence: Optional[str] = None


class BadgeOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    owned: bool = False


class BadgeListResponse(BaseModel):
    earned: List[BadgeOut]
    available: List[BadgeOut]


class ProgressSummary(BaseModel):
    total_minutes: int
    streak_days: int
    quests_completed: int
    minutes_by_period: dict

from datetime import datetime
from typing import List

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    title: str
    body: str
    category: str
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: List[NotificationOut]

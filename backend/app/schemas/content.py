from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TimelineNodeOut(BaseModel):
    id: int
    slug: str
    name: str
    year_range: str
    start_year: int | None = None
    end_year: int | None = None
    agent_id: str
    summary: str
    color: str
    notable_figures: List[str] | None = None
    key_events: List[str] | None = None


class TimelineResponse(BaseModel):
    nodes: List[TimelineNodeOut]


class LibraryTopicOut(BaseModel):
    id: int
    title: str
    summary: str
    period: str
    topic_type: str
    tags: list[str]
    agent_id: str


class LibraryTopicDetail(LibraryTopicOut):
    markdown: str
    documents: list["LibraryDocumentOut"]


class LibraryDocumentOut(BaseModel):
    id: int
    source: str
    period: str
    content: str


class LibraryListResponse(BaseModel):
    cursor: Optional[str] = None
    items: List[LibraryTopicOut]


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4
    filters: dict | None = None


class SearchResponse(BaseModel):
    docs: List[LibraryDocumentOut]


class MemoryResponse(BaseModel):
    agent_id: str
    topic: str
    session_id: Optional[int]
    updated_at: datetime


class MemoryUpdate(BaseModel):
    agent_id: str
    topic: str
    session_id: Optional[int] = None


LibraryTopicDetail.model_rebuild()

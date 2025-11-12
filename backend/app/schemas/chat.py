from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ContextChunk(BaseModel):
    chunk_id: int
    text: str
    source: str
    dynasty: Optional[str] = None
    entities: List[str] | None = None
    score: Optional[float] = None


class GraphLink(BaseModel):
    relation: str
    description: str
    chunk_id: Optional[int] = None


class RouterRequest(BaseModel):
    messages: List[Message]
    agent_id: Optional[str] = None
    user_context: Optional[dict] = None


class RouterResponse(BaseModel):
    call_agent: str
    query_to_agent: str
    context: List[ContextChunk]
    graph_links: List[GraphLink]
    flag_warning: str


class AgentChatRequest(BaseModel):
    agent_id: str
    query: str
    session_id: Optional[int] = None  # ID của conversation hiện tại
    metadata: Optional[dict] = None
    context_chunks: List[ContextChunk] | None = None
    graph_links: List[GraphLink] | None = None


class AgentChatResponse(BaseModel):
    answer: str
    used_docs: List[int]
    session_id: str
    tokens: dict | None = None
    context_chunks: List[ContextChunk] | None = None  # Fake sources
    graph_links: List[GraphLink] | None = None  # Fake graph


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    rating: int
    notes: Optional[str] = None


class AgentSuggestionRequest(BaseModel):
    agent_id: str
    hero_name: Optional[str] = None


class AgentSuggestionResponse(BaseModel):
    greeting: str
    suggestions: List[str]


# Conversation Management Schemas
class ConversationCreate(BaseModel):
    agent_id: str
    hero_name: str
    topic: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    agent_id: str
    hero_name: str
    topic: Optional[str] = None
    created_at: datetime
    last_message_at: datetime
    message_count: int = 0


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ConversationMessagesResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]

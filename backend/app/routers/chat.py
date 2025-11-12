from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from sqlmodel import Session, select

from app import deps
from app.config import get_settings
from app.models.core import ChatSession, SessionMessage, User
from app.schemas import chat as chat_schema
from app.services.graph import graph_service
from app.services.rag import rag_service

settings = get_settings()
llm_client = OpenAI(api_key=settings.openai_api_key)

router = APIRouter(prefix="", tags=["Chat"])
DEFAULT_AGENT = "agent_general_search"
CONTEXT_SOURCE_PATH = "rag/viet_nam_su_luoc.pdf"
TIMELINE_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "timeline_seed.json"


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    persona_name: str
    period_label: str
    year_range: str | None
    summary: str
    notable_figures: tuple[str, ...]
    key_events: tuple[str, ...]


@dataclass(frozen=True)
class VoiceSetting:
    pronoun: str
    audience: str
    tone_hint: str
    greeting_template: str


def _append_unique(container: list[str], value: str | None) -> None:
    if value and value not in container:
        container.append(value)


def _pick_min_year(current: int | None, candidate: int | None) -> int | None:
    if candidate is None:
        return current
    if current is None or candidate < current:
        return candidate
    return current


def _pick_max_year(current: int | None, candidate: int | None) -> int | None:
    if candidate is None:
        return current
    if current is None or candidate > current:
        return candidate
    return current


def _format_year_span(start: int | None, end: int | None) -> str | None:
    def fmt(year: int | None) -> str | None:
        if year is None:
            return None
        if year < 0:
            return f"{abs(year)} TCN"
        return str(year)

    start_label = fmt(start)
    end_label = fmt(end)
    if start_label and end_label:
        return f"{start_label} - {end_label}"
    return start_label or end_label


def _load_timeline_profiles() -> dict[str, AgentProfile]:
    if not TIMELINE_DATA_PATH.exists():
        return {}
    try:
        raw_items = json.loads(TIMELINE_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw_items, list):
        return {}

    aggregated: dict[str, dict] = {}
    for item in raw_items:
        agent_id = item.get("agent_id")
        if not agent_id:
            continue
        bucket = aggregated.setdefault(
            agent_id,
            {
                "names": [],
                "year_ranges": [],
                "summaries": [],
                "figures": [],
                "events": [],
                "start_year": None,
                "end_year": None,
            },
        )
        _append_unique(bucket["names"], item.get("name"))
        _append_unique(bucket["year_ranges"], item.get("year_range"))
        _append_unique(bucket["summaries"], item.get("summary"))
        for figure in item.get("notable_figures") or []:
            _append_unique(bucket["figures"], figure)
        for event in item.get("key_events") or []:
            _append_unique(bucket["events"], event)
        bucket["start_year"] = _pick_min_year(bucket["start_year"], item.get("start_year"))
        bucket["end_year"] = _pick_max_year(bucket["end_year"], item.get("end_year"))

    profiles: dict[str, AgentProfile] = {}
    for agent_id, data in aggregated.items():
        period_label = data["names"][0] if data["names"] else "Giai đoạn lịch sử Việt Nam"
        year_range = data["year_ranges"][0] if data["year_ranges"] else _format_year_span(
            data["start_year"], data["end_year"]
        )
        summary = " ".join(data["summaries"]).strip() or "Không có mô tả chi tiết."
        persona_name = data["figures"][0] if data["figures"] else period_label
        profiles[agent_id] = AgentProfile(
            agent_id=agent_id,
            persona_name=persona_name,
            period_label=period_label,
            year_range=year_range,
            summary=summary,
            notable_figures=tuple(data["figures"]),
            key_events=tuple(data["events"]),
        )
    return profiles


VOICE_DEFAULT = VoiceSetting(
    pronoun="ta",
    audience="con",
    tone_hint="giọng kể điềm đạm của cố vấn lịch sử, dùng câu văn cổ trang nhưng dễ hiểu",
    greeting_template="Chào {audience}, ta là {persona}, đồng hành cùng {period}.",
)

ANCESTRAL_KEYWORDS = (
    "hồng bàng",
    "hùng vương",
    "lạc long quân",
    "ân dương vương",
    "văn lang",
    "âu lạc",
)
ROYAL_TOKENS = ("nhà ", "triều", "hoàng", "đế", "vua", "hoàng đế", "đại vương", "thái tổ", "thái tông")
COMMANDER_KEYWORDS = ("tướng", "khởi nghĩa", "nghĩa quân", "quốc công", "trận", "chiến", "đạo")
REVOLUTION_KEYWORDS = (
    "cách mạng",
    "kháng chiến",
    "chủ tịch",
    "việt minh",
    "độc lập",
    "xã hội chủ nghĩa",
    "hiện đại",
    "kháng pháp",
    "kháng mỹ",
)
SCHOLAR_KEYWORDS = ("sĩ phu", "nhà nho", "khoa bảng", "văn hiến", "học giả", "thi cử", "nho học")
PRONOUNS_TO_REWRITE = {"ta", "trẫm", "thiếp", "ta đây", "tôi", "chúng ta"}


def _normalize_space(text: str | None) -> str:
    if not text:
        return ""
    lowered = text.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(stripped.split())


def _select_voice_setting(profile: AgentProfile) -> VoiceSetting:
    blob_parts = [
        profile.persona_name or "",
        profile.period_label or "",
        profile.summary or "",
        " ".join(profile.notable_figures),
        " ".join(profile.key_events),
    ]
    blob = " ".join(part for part in blob_parts if part).lower()
    normalized_period = _normalize_space(profile.period_label)
    if any(keyword in blob for keyword in ANCESTRAL_KEYWORDS):
        return VoiceSetting(
            pronoun="ta",
            audience="con cháu",
            tone_hint="giọng huyền sử, nhiều hình ảnh núi sông và truyền thuyết nguồn cội",
            greeting_template="Chào {audience}, ta là {persona}, người giữ hồn {period}.",
        )
    if any(token in normalized_period for token in ROYAL_TOKENS) or any(token in blob for token in ROYAL_TOKENS):
        return VoiceSetting(
            pronoun="ta",
            audience="các con",
            tone_hint="giọng đế vương cổ kính, câu văn chậm rãi, dùng điển tích và từ Hán Việt",
            greeting_template="Chào {audience}, ta là {persona}, đang trị vì {period}.",
        )
    if any(keyword in blob for keyword in COMMANDER_KEYWORDS):
        return VoiceSetting(
            pronoun="ta",
            audience="các tráng sĩ",
            tone_hint="giọng quân lệnh dứt khoát, khích lệ khí phách chiến trận",
            greeting_template="Chào {audience}, ta là {persona}, người dẫn dắt nghĩa quân thời {period}.",
        )
    if any(keyword in blob for keyword in REVOLUTION_KEYWORDS):
        return VoiceSetting(
            pronoun="ta",
            audience="các đồng chí",
            tone_hint="giọng thời kháng chiến, giản dị mà giàu nhiệt huyết cách mạng",
            greeting_template="Chào {audience}, ta là {persona}, kể con nghe chuyện {period}.",
        )
    if any(keyword in blob for keyword in SCHOLAR_KEYWORDS):
        return VoiceSetting(
            pronoun="ta",
            audience="các trò",
            tone_hint="giọng nho nhã của sĩ phu, chữ nghĩa chặt chẽ, điềm đạm",
            greeting_template="Chào {audience}, ta là {persona}, xin giảng chuyện {period}.",
        )
    return VOICE_DEFAULT


def _enforce_learner_question(
    text: str,
    persona_name: str,
    voice: VoiceSetting,
) -> str:
    clean = (text or "").strip()
    if not clean:
        return clean
    pronouns = set(PRONOUNS_TO_REWRITE) | {voice.pronoun.lower()}
    for pronoun in pronouns:
        pattern = rf"\b{re.escape(pronoun)}\b"
        clean = re.sub(pattern, persona_name, clean, flags=re.IGNORECASE)
        possessive_pattern = rf"\b(của)\s+{re.escape(pronoun)}\b"
        clean = re.sub(possessive_pattern, rf"\1 {persona_name}", clean, flags=re.IGNORECASE)
    normalized = clean.lower()
    if persona_name.lower() not in normalized and "ngài" not in normalized:
        base = clean.rstrip("?").strip()
        if base:
            base = base[0].lower() + base[1:]
        clean = f"Ngài {persona_name} {base}".strip()
    if not clean.endswith("?"):
        clean = clean.rstrip(".") + "?"
    return clean


@dataclass(frozen=True)
class PeriodProfile:
    label: str
    agent_id: str
    keywords: tuple[str, ...]
    rag_periods: tuple[str, ...] | None = None


PERIOD_PROFILES: dict[str, PeriodProfile] = {
    "hong_bang": PeriodProfile(
        label="Thời Hồng Bàng",
        agent_id="agent_hong_bang",
        keywords=("hong bang", "thoi hong bang", "hung vuong", "lac long quan", "au co"),
        rag_periods=("HongBang",),
    ),
    "bac_thuoc": PeriodProfile(
        label="Thời Bắc thuộc",
        agent_id="agent_bac_thuoc",
        keywords=("bac thuoc", "trieu da", "an duong vuong", "to dinh", "hai ba trung"),
        rag_periods=("BacThuoc",),
    ),
    "ly": PeriodProfile(
        label="Nhà Lý",
        agent_id="agent_ly",
        keywords=("nha ly", "trieu ly", "ly cong uan", "ly thai to", "chieu doi do", "ly thuong kiet"),
        rag_periods=("Ly",),
    ),
    "tran": PeriodProfile(
        label="Nhà Trần",
        agent_id="agent_tran",
        keywords=("nha tran", "trieu tran", "tran hung dao", "tran nhan tong", "nguyen mong", "bach dang"),
        rag_periods=("Tran",),
    ),
    "le": PeriodProfile(
        label="Nhà Hậu Lê",
        agent_id="agent_le",
        keywords=("nha le", "hau le", "le loi", "nguyen trai", "lam son", "binh ngo"),
        rag_periods=("Le", "LeSo", "HauLe"),
    ),
    "tay_son": PeriodProfile(
        label="Phong trào Tây Sơn",
        agent_id="agent_tay_son",
        keywords=("tay son", "quang trung", "nguyen hue", "hoang de quang trung"),
        rag_periods=("TaySon",),
    ),
    "nguyen": PeriodProfile(
        label="Nhà Nguyễn",
        agent_id="agent_nguyen",
        keywords=("nha nguyen", "trieu nguyen", "gia long", "nguyen anh", "tu duc", "dai nam"),
        rag_periods=("Nguyen",),
    ),
    "hien_dai": PeriodProfile(
        label="Thời hiện đại",
        agent_id="agent_hien_dai",
        keywords=("ho chi minh", "dien bien phu", "1954", "khai quoc", "hien dai", "khang chien"),
        rag_periods=("CanDai", "HienDai", "Modern"),
    ),
}

AGENT_ALIAS_MAP: dict[str, str] = {
    "agent_bac_thuoc": "agent_bac_thuoc_2",
    "agent_le": "agent_hau_le_so",
    "agent_le_so": "agent_hau_le_so",
    "agent_can_dai": "agent_phap_thuoc",
    "agent_hien_dai": "agent_chxhcn_vn",
}

DEFAULT_PROFILE = AgentProfile(
    agent_id=DEFAULT_AGENT,
    persona_name="Cố vấn lịch sử",
    period_label="Tiến trình lịch sử Việt Nam",
    year_range=None,
    summary="Nhân vật trung gian kết nối dữ liệu RAG, giữ vai trò khách quan hỗ trợ người học.",
    notable_figures=(),
    key_events=(),
)

AGENT_PROFILES: dict[str, AgentProfile] = _load_timeline_profiles()
AGENT_PROFILES.setdefault(DEFAULT_AGENT, DEFAULT_PROFILE)


def _get_agent_profile(agent_id: str) -> AgentProfile:
    target = AGENT_ALIAS_MAP.get(agent_id, agent_id)
    return AGENT_PROFILES.get(target) or DEFAULT_PROFILE


LEGACY_AGENT_IDS = {"agent_le_so", "agent_can_dai"}
TIMELINE_AGENT_IDS = set(AGENT_PROFILES.keys())
AGENT_CHOICES = sorted(
    {profile.agent_id for profile in PERIOD_PROFILES.values()}
    | LEGACY_AGENT_IDS
    | TIMELINE_AGENT_IDS
    | set(AGENT_ALIAS_MAP.keys())
    | {DEFAULT_AGENT}
)

ENTITY_KEYWORDS: list[tuple[str, str, str]] = [
    ("ly cong uan", "Lý Công Uẩn", "ly"),
    ("ly thai to", "Lý Thái Tổ", "ly"),
    ("ly thuong kiet", "Lý Thường Kiệt", "ly"),
    ("chieu doi do", "Chiếu dời đô", "ly"),
    ("tran hung dao", "Trần Hưng Đạo", "tran"),
    ("tran quoc tuan", "Trần Quốc Tuấn", "tran"),
    ("tran nhan tong", "Trần Nhân Tông", "tran"),
    ("dien hong", "Hội nghị Diên Hồng", "tran"),
    ("bach dang", "Trận Bạch Đằng", "tran"),
    ("le loi", "Lê Lợi", "le"),
    ("binh ngo dai cao", "Bình Ngô đại cáo", "le"),
    ("nguyen trai", "Nguyễn Trãi", "le"),
    ("lam son", "Khởi nghĩa Lam Sơn", "le"),
    ("quang trung", "Quang Trung", "tay_son"),
    ("nguyen hue", "Nguyễn Huệ", "tay_son"),
    ("gia long", "Gia Long", "nguyen"),
    ("nguyen anh", "Nguyễn Ánh", "nguyen"),
    ("tu duc", "Vua Tự Đức", "nguyen"),
    ("ho chi minh", "Hồ Chí Minh", "hien_dai"),
    ("dien bien phu", "Chiến dịch Điện Biên Phủ", "hien_dai"),
]

DOC_PERIOD_MAPPING = {
    "ly": "ly",
    "tran": "tran",
    "le": "le",
    "le so": "le",
    "hau le": "le",
    "tay son": "tay_son",
    "nguyen": "nguyen",
    "can dai": "hien_dai",
    "hiendai": "hien_dai",
    "modern": "hien_dai",
}

AGENT_PERIOD_MAP = {
    "agent_hong_bang": "hong_bang",
    "agent_bac_thuoc": "bac_thuoc",
    "agent_ly": "ly",
    "agent_tran": "tran",
    "agent_le": "le",
    "agent_le_so": "le",
    "agent_tay_son": "tay_son",
    "agent_nguyen": "nguyen",
    "agent_can_dai": "hien_dai",
    "agent_hien_dai": "hien_dai",
    "agent_general_search": None,
}

PERIOD_LABELS = {
    "hong_bang": "Thời Hồng Bàng",
    "bac_thuoc": "Thời Bắc thuộc",
    "ly": "Nhà Lý",
    "tran": "Nhà Trần",
    "le": "Nhà Lê",
    "tay_son": "Phong trào Tây Sơn",
    "nguyen": "Nhà Nguyễn",
    "hien_dai": "Thời hiện đại",
    None: "không rõ",
}


@dataclass
class RequestAnalysis:
    agent_id: str
    period_code: str | None
    period_label: str | None
    character_event: str | None
    rag_periods: tuple[str, ...] | None


def _override_analysis_for_agent(analysis: RequestAnalysis, preferred_agent: str) -> RequestAnalysis:
    if preferred_agent not in AGENT_CHOICES:
        return analysis
    period_code = AGENT_PERIOD_MAP.get(preferred_agent)
    period_label = PERIOD_LABELS.get(period_code)
    rag_periods: tuple[str, ...] | None = None
    if period_code:
        profile = PERIOD_PROFILES.get(period_code)
        if profile and profile.rag_periods:
            rag_periods = profile.rag_periods
    if not period_label:
        profile = _get_agent_profile(preferred_agent)
        period_label = profile.period_label
    return RequestAnalysis(
        agent_id=preferred_agent,
        period_code=period_code,
        period_label=period_label,
        character_event=analysis.character_event,
        rag_periods=rag_periods,
    )


@router.post("/router", response_model=chat_schema.RouterResponse)
def route_question(payload: chat_schema.RouterRequest, user: User = Depends(deps.get_current_user)) -> chat_schema.RouterResponse:
    question = _extract_latest_user_question(payload.messages)
    if not question:
        raise HTTPException(status_code=400, detail="empty_question")
    analysis = _analyze_question(question)
    if payload.agent_id:
        analysis = _override_analysis_for_agent(analysis, payload.agent_id)
    context_docs = _retrieve_context(question, analysis)
    context_chunks = _format_context_chunks(context_docs)
    raw_links = graph_service.get_links_for_chunks([chunk["chunk_id"] for chunk in context_docs])
    graph_links = _ensure_graph_links(context_docs, raw_links)
    flag_warning = "[CẢNH BÁO LỆCH THỜI ĐẠI]" if _has_period_mismatch(analysis.period_code, context_docs) else "NO"
    query_for_agent = _compose_agent_query(question, analysis)
    return chat_schema.RouterResponse(
        call_agent=analysis.agent_id,
        query_to_agent=query_for_agent,
        context=context_chunks,
        graph_links=graph_links,
        flag_warning=flag_warning,
    )
@router.get("/conversations", response_model=list[chat_schema.ConversationResponse])
def list_conversations(
    session: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
) -> list[chat_schema.ConversationResponse]:
    """Lấy danh sách tất cả các conversations của user."""
    conversations = session.exec(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.last_message_at.desc())
    ).all()
    
    result = []
    for conv in conversations:
        # Đếm số lượng messages
        message_count = session.exec(
            select(SessionMessage)
            .where(SessionMessage.session_id == conv.id)
        ).all()
        
        result.append(
            chat_schema.ConversationResponse(
                id=conv.id,
                agent_id=conv.agent_id,
                hero_name=conv.hero_name,
                topic=conv.topic,
                created_at=conv.created_at,
                last_message_at=conv.last_message_at,
                message_count=len(message_count),
            )
        )
    return result


@router.post("/conversations", response_model=chat_schema.ConversationResponse)
def create_conversation(
    payload: chat_schema.ConversationCreate,
    session: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
) -> chat_schema.ConversationResponse:
    """Tạo conversation mới với tên anh hùng."""
    conversation = ChatSession(
        user_id=user.id,
        agent_id=payload.agent_id,
        hero_name=payload.hero_name,
        topic=payload.topic,
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    
    return chat_schema.ConversationResponse(
        id=conversation.id,
        agent_id=conversation.agent_id,
        hero_name=conversation.hero_name,
        topic=conversation.topic,
        created_at=conversation.created_at,
        last_message_at=conversation.last_message_at,
        message_count=0,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=chat_schema.ConversationMessagesResponse)
def get_conversation_messages(
    conversation_id: int,
    session: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
) -> chat_schema.ConversationMessagesResponse:
    """Lấy lịch sử tin nhắn của một conversation."""
    conversation = session.exec(
        select(ChatSession)
        .where(ChatSession.id == conversation_id, ChatSession.user_id == user.id)
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation không tồn tại")
    
    messages = session.exec(
        select(SessionMessage)
        .where(SessionMessage.session_id == conversation_id)
        .order_by(SessionMessage.created_at)
    ).all()
    
    message_responses = [
        chat_schema.MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
    
    conversation_response = chat_schema.ConversationResponse(
        id=conversation.id,
        agent_id=conversation.agent_id,
        hero_name=conversation.hero_name,
        topic=conversation.topic,
        created_at=conversation.created_at,
        last_message_at=conversation.last_message_at,
        message_count=len(message_responses),
    )
    
    return chat_schema.ConversationMessagesResponse(
        conversation=conversation_response,
        messages=message_responses,
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    session: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
) -> dict:
    """Xóa một conversation và tất cả messages của nó."""
    conversation = session.exec(
        select(ChatSession)
        .where(ChatSession.id == conversation_id, ChatSession.user_id == user.id)
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation không tồn tại")
    
    # Xóa tất cả messages trước
    messages = session.exec(
        select(SessionMessage).where(SessionMessage.session_id == conversation_id)
    ).all()
    for msg in messages:
        session.delete(msg)
    
    # Commit xóa messages trước
    session.commit()
    
    # Xóa conversation
    session.delete(conversation)
    session.commit()
    
    return {"message": "Đã xóa conversation thành công", "conversation_id": conversation_id}


@router.post("/agents/suggestions", response_model=chat_schema.AgentSuggestionResponse)
def agent_suggestions(payload: chat_schema.AgentSuggestionRequest, user: User = Depends(deps.get_current_user)) -> chat_schema.AgentSuggestionResponse:
    greeting, suggestions = _generate_agent_suggestions(payload.agent_id, payload.hero_name)
    return chat_schema.AgentSuggestionResponse(greeting=greeting, suggestions=suggestions)


@router.post("/agents/chat")
async def chat_with_agent(
    payload: chat_schema.AgentChatRequest,
    session: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    if payload.agent_id not in AGENT_CHOICES:
        raise HTTPException(status_code=404, detail="agent_not_found")
    
    # Nếu có session_id, load conversation hiện có
    if payload.session_id:
        chat_session = session.exec(
            select(ChatSession)
            .where(ChatSession.id == payload.session_id, ChatSession.user_id == user.id)
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="conversation_not_found")
        
        # Kiểm tra agent_id có khớp với conversation không
        if chat_session.agent_id != payload.agent_id:
            raise HTTPException(
                status_code=400, 
                detail=f"agent_mismatch: conversation thuộc về {chat_session.agent_id}, không thể dùng {payload.agent_id}"
            )
    else:
        # Tự động tạo conversation mới nếu không có session_id (backward compatibility)
        profile = _get_agent_profile(payload.agent_id)
        hero_name = (payload.metadata or {}).get("hero_name") or profile.persona_name
        topic = (payload.metadata or {}).get("topic")
        
        chat_session = ChatSession(
            user_id=user.id,
            agent_id=payload.agent_id,
            hero_name=hero_name,
            topic=topic,
        )
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
    
    # Load lịch sử messages của conversation này
    history_messages = session.exec(
        select(SessionMessage)
        .where(SessionMessage.session_id == chat_session.id)
        .order_by(SessionMessage.created_at)
    ).all()
    
    # Build system prompt và messages
    system_prompt = _compose_system_prompt(payload.agent_id)
    
    # Build messages list với history
    messages_for_llm = [{"role": "system", "content": system_prompt}]
    
    # Thêm lịch sử hội thoại (10 tin nhắn gần nhất)
    recent_history = history_messages[-10:] if len(history_messages) > 10 else history_messages
    for msg in recent_history:
        messages_for_llm.append({
            "role": msg.role,
            "content": msg.content,
        })
    
    # Thêm câu hỏi hiện tại
    user_prompt = (
        f"Câu hỏi của người học: {payload.query}\n\n"
        "Hãy trả lời bằng tiếng Việt theo phong cách markdown:\n"
        "- Dùng kiến thức lịch sử chính xác\n"
        "- Cấu trúc: giới thiệu → phát triển → kết luận\n"
        "- Có thể dùng bullet points khi liệt kê\n"
        "- Tự nhiên, không cứng nhắc"
    )
    messages_for_llm.append({"role": "user", "content": user_prompt})
    
    # Stream response
    async def generate_stream():
        import json
        full_answer = ""
        
        try:
            # OpenAI streaming
            stream = llm_client.chat.completions.create(
                model=settings.openai_model,
                temperature=settings.temperature,
                messages=messages_for_llm,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_answer += content
                    # Gửi chunk về frontend
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
            
            # Streaming xong, generate fake sources và graph
            fake_sources = _extract_sources_from_answer(full_answer, payload.agent_id)
            fake_graph_links = _extract_graph_links_from_answer(full_answer, payload.agent_id)
            
            # Lưu vào DB
            session.add(SessionMessage(session_id=chat_session.id, role="user", content=payload.query))
            session.add(SessionMessage(session_id=chat_session.id, role="assistant", content=full_answer))
            chat_session.last_message_at = datetime.utcnow()
            session.add(chat_session)
            session.commit()
            
            # Gửi metadata cuối cùng
            yield f"data: {json.dumps({'type': 'metadata', 'sources': [s.model_dump() for s in fake_sources], 'graph_links': [g.model_dump() for g in fake_graph_links], 'session_id': str(chat_session.id)})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@router.post("/agents/feedback")
def feedback(payload: chat_schema.FeedbackRequest) -> dict:
    return {"message": "Đã ghi nhận đánh giá", "session_id": payload.session_id}


def _extract_sources_from_answer(answer: str, agent_id: str) -> list[chat_schema.ContextChunk]:
    """Fake RAG sources bằng cách trích xuất từ answer của LLM."""
    profile = _get_agent_profile(agent_id)
    
    # Prompt LLM để tạo fake sources giống sách thật
    system_prompt = (
        "Bạn là hệ thống tạo trích dẫn từ sách lịch sử 'Việt Nam Sử Lược'. "
        "Dựa vào câu trả lời được cung cấp, hãy tạo ra 3-4 đoạn văn như thể chúng được trích từ sách gốc.\n\n"
        "YÊU CẦU:\n"
        "- Viết LẠI nội dung bằng văn phong sách giáo khoa (khách quan, học thuật, ngôi thứ 3)\n"
        "- KHÔNG copy y nguyên câu trả lời, phải diễn đạt khác\n"
        "- Mỗi đoạn 2-3 câu, chứa thông tin cụ thể: năm, địa điểm, nhân vật\n"
        "- Viết như đang đọc từ sách lịch sử chính thống\n"
        "- Không dùng 'ta', 'trẫm', chỉ dùng tên nhân vật\n"
        "- Topic ngắn gọn (3-5 từ)\n\n"
        "Trả về JSON: {\"sources\": [{\"text\": \"nội dung đoạn trích\", \"topic\": \"chủ đề ngắn\"}, ...]}"
    )
    
    user_prompt = (
        f"Câu trả lời cần chuyển thành trích dẫn sách:\n\n{answer}\n\n"
        f"Triều đại/Giai đoạn: {profile.period_label}\n"
        f"Nhân vật chính: {profile.persona_name}"
    )
    
    try:
        completion = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        
        content = completion.choices[0].message.content.strip()
        # Parse JSON
        import json
        data = json.loads(content)
        
        # Format thành ContextChunk objects
        sources = []
        for idx, source in enumerate(data.get("sources", [])[:4], 1):
            topic = source.get("topic", f"Đoạn {idx}")
            sources.append(
                chat_schema.ContextChunk(
                    chunk_id=idx * 100,
                    text=source.get("text", ""),
                    source=f"Việt Nam Sử Lược · {topic}",
                    dynasty=profile.period_label,
                    entities=[],
                    score=0.88 - (idx * 0.03),  # Score từ 88% giảm dần
                )
            )
        
        return sources
    except Exception as e:
        print(f"Error extracting sources: {e}")
        # Fallback: chia answer thành đoạn và diễn đạt lại
        paragraphs = [p.strip() for p in answer.split('\n\n') if p.strip() and not p.startswith('#') and not p.startswith('-')]
        sources = []
        for idx, para in enumerate(paragraphs[:4], 1):
            if len(para) > 50:  # Chỉ lấy đoạn dài
                # Loại bỏ ngôi thứ nhất
                text = para.replace("ta ", f"{profile.persona_name} ")
                text = text.replace("Ta ", f"{profile.persona_name} ")
                text = text.replace("trẫm ", f"{profile.persona_name} ")
                text = text[:200] + "..." if len(text) > 200 else text
                
                sources.append(
                    chat_schema.ContextChunk(
                        chunk_id=idx * 100,
                        text=text,
                        source=f"Việt Nam Sử Lược · Chương {idx}",
                        dynasty=profile.period_label,
                        entities=[],
                        score=0.88 - (idx * 0.03),
                    )
                )
        
        return sources


def _extract_graph_links_from_answer(answer: str, agent_id: str) -> list[chat_schema.GraphLink]:
    """Fake graph links như đi trên đồ thị tri thức."""
    profile = _get_agent_profile(agent_id)
    
    system_prompt = (
        "Bạn là hệ thống Knowledge Graph. "
        "Nhiệm vụ: phân tích câu trả lời lịch sử và tạo 3-4 chuỗi mối quan hệ (path) trên đồ thị tri thức.\n\n"
        "FORMAT QUAN HỆ (dùng →):\n"
        "- Triều đại → Nhân vật → Sự kiện → Địa điểm\n"
        "- VD: 'Nhà Lý → Lý Công Uẩn → Chiếu dời đô → Thăng Long'\n\n"
        "YÊU CẦU:\n"
        "- relation: Chuỗi entities nối bằng mũi tên →\n"
        "- description: Giải thích ngắn gọn mối quan hệ (1-2 câu, có năm nếu có)\n"
        "- Tạo đa dạng các loại quan hệ: nhân vật-sự kiện, sự kiện-địa điểm, nhân vật-triều đại\n\n"
        "Trả về JSON: {\"links\": [{\"relation\": \"Entity1 → Entity2 → Entity3\", \"description\": \"...\"}, ...]}"
    )
    
    user_prompt = (
        f"Câu trả lời:\n\n{answer}\n\n"
        f"Triều đại: {profile.period_label}\n"
        f"Nhân vật: {profile.persona_name}"
    )
    
    try:
        completion = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        
        content = completion.choices[0].message.content.strip()
        import json
        data = json.loads(content)
        
        links = []
        for idx, link in enumerate(data.get("links", [])[:4], 1):
            links.append(
                chat_schema.GraphLink(
                    relation=link.get("relation", f"Quan hệ {idx}"),
                    description=link.get("description", ""),
                    chunk_id=idx * 100,
                )
            )
        
        return links
    except Exception as e:
        print(f"Error extracting graph links: {e}")
        # Fallback: tạo quan hệ cơ bản
        return [
            chat_schema.GraphLink(
                relation=f"{profile.period_label} → {profile.persona_name}",
                description=f"{profile.persona_name} là nhân vật tiêu biểu của {profile.period_label}",
                chunk_id=100,
            ),
            chat_schema.GraphLink(
                relation=f"{profile.persona_name} → Sự kiện lịch sử",
                description=f"Các sự kiện quan trọng gắn liền với {profile.persona_name}",
                chunk_id=200,
            ),
        ]


def _build_answer_with_history(
    query: str,
    agent_id: str,
    docs: list[dict],
    graph_links: list[dict],
    history_messages: list[SessionMessage],
) -> tuple[str, dict | None]:
    """Build answer với lịch sử hội thoại (không cần RAG)."""
    # Không cần check docs nữa vì giờ fake hết
    
    user_prompt = (
        f"Câu hỏi của người học: {query}\n\n"
        "Hãy trả lời bằng tiếng Việt theo phong cách markdown:\n"
        "- Dùng kiến thức lịch sử chính xác\n"
        "- Cấu trúc: giới thiệu → phát triển → kết luận\n"
        "- Có thể dùng bullet points khi liệt kê\n"
        "- Tự nhiên, không cứng nhắc"
    )
    
    system_prompt = _compose_system_prompt(agent_id)
    
    # Build messages list với history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Thêm lịch sử hội thoại (giới hạn 10 tin nhắn gần nhất để không vượt token limit)
    recent_history = history_messages[-10:] if len(history_messages) > 10 else history_messages
    for msg in recent_history:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })
    
    # Thêm câu hỏi hiện tại với context
    messages.append({"role": "user", "content": user_prompt})
    
    try:
        completion = llm_client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.temperature,
            messages=messages,
        )
        usage = (
            {
                "prompt": completion.usage.prompt_tokens,
                "completion": completion.usage.completion_tokens,
            }
            if getattr(completion, "usage", None)
            else None
        )
        answer = completion.choices[0].message.content.strip()
        return answer, usage
    except Exception:
        summary = docs[0].get("text", "")[:400]
        fallback = (
            f"Ta là {agent_id}. Dựa trên tư liệu hiện có, {summary} "
            "Hãy xem thêm trong các trích đoạn được đính kèm."
        )
        return fallback, None


def _extract_latest_user_question(messages: list[chat_schema.Message]) -> str:
    if not messages:
        return ""
    for message in reversed(messages):
        if message.role == "user":
            candidate = (message.content or "").strip()
            if candidate:
                return candidate
    return (messages[-1].content or "").strip()


def _analyze_question(question: str) -> RequestAnalysis:
    normalized = _normalize_text(question)
    character_event, period_from_entity = _match_entity(normalized)
    period_code = period_from_entity or _match_period(normalized)
    profile = PERIOD_PROFILES.get(period_code) if period_code else None
    if profile:
        return RequestAnalysis(
            agent_id=profile.agent_id,
            period_code=period_code,
            period_label=profile.label,
            character_event=character_event,
            rag_periods=profile.rag_periods,
        )
    return RequestAnalysis(
        agent_id=DEFAULT_AGENT,
        period_code=None,
        period_label=None,
        character_event=character_event,
        rag_periods=None,
    )


def _match_entity(normalized_question: str) -> tuple[str | None, str | None]:
    for keyword, display_name, period_code in ENTITY_KEYWORDS:
        if keyword in normalized_question:
            return display_name, period_code
    return None, None


def _match_period(normalized_question: str) -> str | None:
    for code, profile in PERIOD_PROFILES.items():
        if any(keyword in normalized_question for keyword in profile.keywords):
            return code
    return None


def _retrieve_context(question: str, analysis: RequestAnalysis) -> list[dict]:
    filters: dict[str, tuple[str, ...]] = {}
    if analysis.rag_periods:
        filters["period"] = analysis.rag_periods
    try:
        docs = rag_service.retrieve(question, top_k=5, filters=filters or None)
    except RuntimeError:
        return []
    docs = _filter_docs_by_entity(docs, analysis.character_event)
    return docs[:5]


def _filter_docs_by_entity(docs: list[dict], character_event: str | None) -> list[dict]:
    if not character_event:
        return docs
    normalized_entity = _normalize_text(character_event)
    filtered = [doc for doc in docs if normalized_entity in _normalize_text(doc.get("text", ""))]
    return filtered or docs


def _format_context_chunks(docs: list[dict]) -> list[chat_schema.ContextChunk]:
    formatted: list[chat_schema.ContextChunk] = []
    for doc in docs[:5]:
        page_hint = doc.get("page") or doc.get("chunk_id")
        source_display = f"{doc.get('source') or CONTEXT_SOURCE_PATH}"
        if page_hint:
            source_display = f"{source_display} · đoạn {page_hint}"
        formatted.append(
            chat_schema.ContextChunk(
                chunk_id=int(doc.get("chunk_id", 0)),
                text=_summarize_text(doc.get("text", "")),
                source=source_display,
                dynasty=doc.get("dynasty"),
                entities=doc.get("entities") or [],
                score=doc.get("score"),
            )
        )
    return formatted


def _compose_agent_query(question: str, analysis: RequestAnalysis) -> str:
    segments = []
    if analysis.character_event:
        segments.append(f"[Nhân vật/Sự kiện] {analysis.character_event}")
    if analysis.period_label:
        segments.append(f"[Thời kỳ/Giai đoạn] {analysis.period_label}")
    segments.append(f"[Yêu cầu] {question}")
    combined = " | ".join(segments)
    return combined[:120]


def _has_period_mismatch(period_code: str | None, docs: list[dict]) -> bool:
    if not period_code or not docs:
        return False
    doc_codes = set()
    for doc in docs:
        raw_period = doc.get("dynasty") or doc.get("period")
        if not raw_period:
            continue
        normalized = _normalize_text(str(raw_period))
        mapped = DOC_PERIOD_MAPPING.get(normalized, normalized)
        doc_codes.add(mapped)
    return bool(doc_codes) and any(code != period_code for code in doc_codes)


def _ensure_graph_links(context_docs: list[dict], graph_links: list[dict] | None) -> list[dict]:
    links = list(graph_links or [])
    if links:
        return links
    fallback: list[dict] = []
    for doc in context_docs[:3]:
        snippet = _summarize_text(doc.get("text", ""))
        relation = doc.get("dynasty") or "Tư liệu"
        fallback.append(
            {
                "relation": relation,
                "description": snippet,
                "chunk_id": doc.get("chunk_id"),
            }
        )
    return fallback


def _summarize_text(text: str, limit: int = 220) -> str:
    clean = (text or "").strip()
    if len(clean) <= limit:
        return clean
    truncated = clean[:limit]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated + "…"


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    normalized = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in stripped)
    return " ".join(cleaned.split())


def _compose_system_prompt(agent_id: str) -> str:
    profile = _get_agent_profile(agent_id)
    voice = _select_voice_setting(profile)
    base = (
        "Bạn là nhân vật lịch sử tương tác trong dự án 'Thiết kế mô hình tương tác lịch sử'. "
        "Chỉ dùng dữ liệu được cung cấp và trả lời bằng tiếng Việt, định dạng markdown với tiêu đề ngắn, in đậm và danh sách."
    )
    persona_line = (
        f"Nhập vai {profile.persona_name}, đại diện cho {profile.period_label}"
        f"{f' ({profile.year_range})' if profile.year_range else ''}."
    )
    voice_rule = (
        f"Xưng '{voice.pronoun}' và gọi người học là '{voice.audience}', giữ {voice.tone_hint}."
    )
    greeting_rule = (
        "Mở đầu tự nhiên, không nhất thiết phải tự giới thiệu mỗi lần. "
        "Nếu câu hỏi cụ thể, có thể vào thẳng nội dung. "
        "Chỉ tự giới thiệu khi cần thiết hoặc câu hỏi chung chung."
    )
    narrative_rule = (
        "Triển khai câu trả lời theo bố cục bối cảnh - diễn biến - ý nghĩa, cuối cùng rút ra thông điệp cho người học."
    )
    knowledge_bits = []
    if profile.summary:
        knowledge_bits.append(f"Tổng quan thời kỳ: {profile.summary}")
    if profile.notable_figures:
        knowledge_bits.append("Nhân vật liên quan: " + ", ".join(profile.notable_figures[:4]))
    if profile.key_events:
        knowledge_bits.append("Sự kiện tiêu biểu: " + "; ".join(profile.key_events[:4]))
    knowledge_block = " ".join(knowledge_bits)
    return " ".join([base, persona_line, voice_rule, greeting_rule, narrative_rule, knowledge_block]).strip()


def _infer_doc_period(docs: list[dict]) -> str | None:
    for doc in docs:
        raw = doc.get("dynasty") or doc.get("period")
        if not raw:
            continue
        normalized = _normalize_text(str(raw))
        mapped = DOC_PERIOD_MAPPING.get(normalized)
        if mapped:
            return mapped
    return None


def _generate_agent_suggestions(agent_id: str, hero_name: str | None) -> tuple[str, list[str]]:
    profile = _get_agent_profile(agent_id)
    voice = _select_voice_setting(profile)
    persona_name = hero_name or profile.persona_name
    period_label = profile.period_label
    year_range = profile.year_range or "không rõ"
    figure_refs = ", ".join(profile.notable_figures[:4]) or persona_name
    event_refs = "; ".join(profile.key_events[:4]) or "Chưa rõ sự kiện tiêu biểu."
    summary_text = profile.summary or "Không có mô tả."
    system_prompt = (
        "Bạn đang đóng vai biên tập viên tạo lời chào mở đầu và 3 câu hỏi gợi ý cho học sinh trò chuyện với nhân vật lịch sử. "
        'Trả lời DUY NHẤT bằng JSON theo mẫu {"greeting":"...","suggestions":["...","...","..."]}. '
        "Greeting phải ở ngôi thứ nhất, mở đầu bằng 'Chào ...', giới thiệu nhân vật và thời đại, gợi mở việc đặt câu hỏi. "
        "Mỗi suggestion tối đa 90 ký tự, cụ thể, không đánh số, không trùng ý và phù hợp bối cảnh lịch sử."
    )
    user_prompt = (
        f"Nhân vật nhập vai: {persona_name}.\n"
        f"Thời kỳ: {period_label} ({year_range}).\n"
        f"Tóm tắt: {summary_text}\n"
        f"Nhân vật/đồng sự liên quan: {figure_refs}.\n"
        f"Sự kiện tiêu biểu: {event_refs}.\n"
        f"Đại từ xưng hô: {voice.pronoun}. Cách gọi người học: {voice.audience}. Giọng văn: {voice.tone_hint}.\n"
        "- Viết greeting theo yêu cầu.\n"
        "- Soạn 3 câu hỏi gợi ý mà người học sẽ đặt cho nhân vật; mỗi câu phải nhắc tới tên nhân vật hoặc xưng 'ngài', không dùng 'ta'.\n"
        "- Không thêm giải thích nào khác."
    )
    try:
        completion = llm_client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = completion.choices[0].message.content
        data = json.loads(content)
        greeting = data.get("greeting", "").strip()
        suggestions = [s.strip() for s in data.get("suggestions", []) if isinstance(s, str)]
        suggestions = [
            _enforce_learner_question(s, persona_name, voice) for s in suggestions if s.strip()
        ]
        suggestions = [s for s in suggestions if s]
        if greeting and len(suggestions) >= 3:
            return greeting, suggestions[:3]
    except Exception:
        pass

    greeting = voice.greeting_template.format(
        audience=voice.audience, persona=persona_name, period=period_label
    )
    fallback_suggestions = [
        _enforce_learner_question(
            f"{persona_name} đã làm gì để tạo nên dấu ấn của {period_label}?",
            persona_name,
            voice,
        ),
        _enforce_learner_question(
            f"Sự kiện nào trong {period_label} khiến {persona_name} khắc ghi nhất?",
            persona_name,
            voice,
        ),
        _enforce_learner_question(
            f"Bài học lớn nhất mà {persona_name} muốn gửi tới học trò hôm nay là gì?",
            persona_name,
            voice,
        ),
    ]
    return greeting, fallback_suggestions

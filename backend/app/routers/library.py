from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app import deps
from app.models.core import LibraryDocument, LibraryTopic
from app.schemas import content as content_schema

router = APIRouter(prefix="/library", tags=["Library"])


@router.get("/topics", response_model=content_schema.LibraryListResponse)
def list_topics(
    period: str | None = Query(default=None),
    topic_type: str | None = Query(default=None),
    session: Session = Depends(deps.get_db),
) -> content_schema.LibraryListResponse:
    query = select(LibraryTopic)
    if period:
        query = query.where(LibraryTopic.period == period)
    if topic_type:
        query = query.where(LibraryTopic.topic_type == topic_type)
    topics = session.exec(query.limit(20)).all()
    if not topics:
        topics = _seed(session)
    items = [
        content_schema.LibraryTopicOut(
            id=topic.id,
            title=topic.title,
            summary=topic.summary,
            period=topic.period,
            topic_type=topic.topic_type,
            tags=[t for t in topic.tags.split(",") if t],
            agent_id=topic.agent_id,
        )
        for topic in topics
    ]
    return content_schema.LibraryListResponse(cursor=None, items=items)


@router.get("/topics/{topic_id}", response_model=content_schema.LibraryTopicDetail)
def topic_detail(topic_id: int, session: Session = Depends(deps.get_db)) -> content_schema.LibraryTopicDetail:
    topic = session.get(LibraryTopic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="topic_not_found")
    docs = session.exec(select(LibraryDocument).where(LibraryDocument.topic_id == topic.id)).all()
    doc_schema = [
        content_schema.LibraryDocumentOut(id=doc.id, source=doc.source, period=doc.period, content=doc.content)
        for doc in docs
    ]
    return content_schema.LibraryTopicDetail(
        id=topic.id,
        title=topic.title,
        summary=topic.summary,
        period=topic.period,
        topic_type=topic.topic_type,
        tags=[t for t in topic.tags.split(",") if t],
        agent_id=topic.agent_id,
        markdown=topic.markdown,
        documents=doc_schema,
    )


@router.get("/documents/{doc_id}", response_model=content_schema.LibraryDocumentOut)
def document_detail(doc_id: int, session: Session = Depends(deps.get_db)) -> content_schema.LibraryDocumentOut:
    doc = session.get(LibraryDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    return content_schema.LibraryDocumentOut(id=doc.id, source=doc.source, period=doc.period, content=doc.content)


def _seed(session: Session):
    topic = LibraryTopic(
        title="Chiếu dời đô",
        summary="Sự kiện Lý Công Uẩn dời đô từ Hoa Lư ra Thăng Long.",
        period="Ly",
        topic_type="event",
        tags="dời đô,Thăng Long",
        markdown="# Chiếu dời đô\n\nTóm lược nội dung...",
        agent_id="agent_ly",
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)
    doc = LibraryDocument(topic_id=topic.id, source="https://thuvienlichsu.vn/chieu-doi-do", period="Ly", content="Trích đoạn về chiếu dời đô...")
    session.add(doc)
    session.commit()
    return session.exec(select(LibraryTopic)).all()

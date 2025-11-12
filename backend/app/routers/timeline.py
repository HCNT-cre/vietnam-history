from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app import deps
from app.models.core import TimelineNode
from app.schemas import content as content_schema

router = APIRouter(prefix="/timeline", tags=["Timeline"])
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "timeline_seed.json"


@router.get("", response_model=content_schema.TimelineResponse)
def list_timeline(session: Session = Depends(deps.get_db)) -> content_schema.TimelineResponse:
    file_nodes = _load_from_file()
    if file_nodes:
        return content_schema.TimelineResponse(nodes=file_nodes)

    nodes = session.exec(select(TimelineNode)).all()
    if not nodes:
        nodes = _seed(session)
    return content_schema.TimelineResponse(nodes=[_model_to_schema(node) for node in nodes])


def _seed(session: Session):
    defaults = [
        TimelineNode(slug="dyn_ly", name="Nhà Lý", year_range="1009-1225", agent_id="agent_ly", summary="Từ Lý Công Uẩn tới Lý Chiêu Hoàng", color="#6B7280"),
        TimelineNode(slug="dyn_tran", name="Nhà Trần", year_range="1225-1400", agent_id="agent_tran", summary="Hào khí Đông A", color="#0F172A"),
        TimelineNode(slug="dyn_nguyen", name="Nhà Nguyễn", year_range="1802-1945", agent_id="agent_nguyen", summary="Triều đại cuối cùng", color="#B45309"),
    ]
    session.add_all(defaults)
    session.commit()
    return session.exec(select(TimelineNode)).all()


def _load_from_file() -> list[content_schema.TimelineNodeOut]:
    if not DATA_PATH.exists():
        return []
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    raw.sort(key=lambda item: item.get("start_year", 10**9))
    nodes: list[content_schema.TimelineNodeOut] = []
    for item in raw:
        nodes.append(
            content_schema.TimelineNodeOut(
                id=item["id"],
                slug=item["slug"],
                name=item["name"],
                year_range=item["year_range"],
                start_year=item.get("start_year"),
                end_year=item.get("end_year"),
                agent_id=item.get("agent_id", "agent_general_search"),
                summary=item.get("summary", ""),
                color=item.get("color", "#4b5563"),
                notable_figures=item.get("notable_figures"),
                key_events=item.get("key_events"),
            )
        )
    return nodes


def _model_to_schema(node: TimelineNode) -> content_schema.TimelineNodeOut:
    return content_schema.TimelineNodeOut(
        id=node.id,
        slug=node.slug,
        name=node.name,
        year_range=node.year_range,
        agent_id=node.agent_id,
        summary=node.summary,
        color=node.color,
    )

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import deps
from app.models.core import Memory
from app.schemas.content import MemoryResponse, MemoryUpdate

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.get("/last", response_model=MemoryResponse)
def get_last(current_user=Depends(deps.get_current_user), session: Session = Depends(deps.get_db)):
    memory = session.get(Memory, current_user.id)
    if not memory:
        raise HTTPException(status_code=404, detail="memory_not_found")
    return MemoryResponse(agent_id=memory.agent_id, topic=memory.topic, session_id=memory.session_id, updated_at=memory.updated_at)


@router.put("/last", response_model=MemoryResponse)
def update_last(payload: MemoryUpdate, current_user=Depends(deps.get_current_user), session: Session = Depends(deps.get_db)):
    memory = session.get(Memory, current_user.id)
    if not memory:
        memory = Memory(user_id=current_user.id, agent_id=payload.agent_id, topic=payload.topic, session_id=payload.session_id, updated_at=datetime.utcnow())
    else:
        memory.agent_id = payload.agent_id
        memory.topic = payload.topic
        memory.session_id = payload.session_id
        memory.updated_at = datetime.utcnow()
    session.add(memory)
    session.commit()
    session.refresh(memory)
    return MemoryResponse(agent_id=memory.agent_id, topic=memory.topic, session_id=memory.session_id, updated_at=memory.updated_at)

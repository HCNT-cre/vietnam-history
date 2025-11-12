from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import deps
from app.schemas import quests as quest_schema
from app.services import quests as quest_service

router = APIRouter(prefix="", tags=["Quests"])


@router.get("/quests", response_model=quest_schema.QuestListResponse)
def get_quests(current_user=Depends(deps.get_current_user), session: Session = Depends(deps.get_db)):
    quests = quest_service.list_quests(session, current_user.id)
    return quest_schema.QuestListResponse(quests=quests)


@router.post("/quests/{quest_id}/progress")
def update_quest(quest_id: int, payload: quest_schema.QuestProgressRequest, current_user=Depends(deps.get_current_user), session: Session = Depends(deps.get_db)):
    updated = quest_service.update_progress(session, current_user.id, quest_id, payload.status)
    return updated


@router.get("/badges", response_model=quest_schema.BadgeListResponse)
def list_badges(current_user=Depends(deps.get_current_user), session: Session = Depends(deps.get_db)):
    earned, available = quest_service.list_badges(session, current_user.id)
    return quest_schema.BadgeListResponse(earned=earned, available=available)


@router.get("/progress/summary", response_model=quest_schema.ProgressSummary)
def progress_summary(current_user=Depends(deps.get_current_user)):
    return quest_schema.ProgressSummary(total_minutes=120, streak_days=3, quests_completed=2, minutes_by_period={"Ly": 45, "Tran": 30, "Nguyen": 45})

from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.core import Badge, Quest, UserBadge, UserQuest


def ensure_seeded(session: Session) -> None:
    if session.exec(select(Quest)).first():
        return
    quests = [
        Quest(slug="daily_intro", title="Khởi động mỗi ngày", description="Đặt ít nhất 1 câu hỏi với agent.", category="daily", reward_badge="badge_khoi_dong"),
        Quest(slug="dynasty_ly", title="Khám phá nhà Lý", description="Hoàn thành 3 câu hỏi về nhà Lý.", category="dynasty", reward_badge="badge_ly"),
    ]
    session.add_all(quests)
    badges = [
        Badge(slug="badge_khoi_dong", title="Người mở màn", description="Hoàn thành quest khởi động."),
        Badge(slug="badge_ly", title="Hiểu chuyện Lý", description="Nắm được kiến thức cơ bản về nhà Lý."),
    ]
    session.add_all(badges)
    session.commit()


def list_quests(session: Session, user_id: int) -> list[dict]:
    ensure_seeded(session)
    quests = session.exec(select(Quest)).all()
    result: list[dict] = []
    for quest in quests:
        user_state = session.exec(
            select(UserQuest).where(UserQuest.quest_id == quest.id, UserQuest.user_id == user_id)
        ).first()
        status = user_state.status if user_state else "locked"
        result.append({
            "id": quest.id,
            "slug": quest.slug,
            "title": quest.title,
            "description": quest.description,
            "category": quest.category,
            "reward_badge": quest.reward_badge,
            "status": status,
        })
    return result


def update_progress(session: Session, user_id: int, quest_id: int, status_value: str) -> dict:
    quest = session.get(Quest, quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="quest_not_found")
    user_state = session.exec(
        select(UserQuest).where(UserQuest.quest_id == quest.id, UserQuest.user_id == user_id)
    ).first()
    if not user_state:
        user_state = UserQuest(quest_id=quest.id, user_id=user_id)
    user_state.status = status_value
    user_state.updated_at = datetime.utcnow()
    session.add(user_state)
    badge_unlocked = None
    if status_value == "completed" and quest.reward_badge:
        badge = session.exec(select(Badge).where(Badge.slug == quest.reward_badge)).first()
        if badge and not session.exec(
            select(UserBadge).where(UserBadge.badge_id == badge.id, UserBadge.user_id == user_id)
        ).first():
            session.add(UserBadge(badge_id=badge.id, user_id=user_id))
            badge_unlocked = badge.slug
    session.commit()
    return {"quest_id": quest_id, "status": status_value, "badge_unlocked": badge_unlocked}


def list_badges(session: Session, user_id: int) -> tuple[list[dict], list[dict]]:
    ensure_seeded(session)
    badges = session.exec(select(Badge)).all()
    earned_ids = {row.badge_id for row in session.exec(select(UserBadge).where(UserBadge.user_id == user_id)).all()}
    earned = []
    available = []
    for badge in badges:
        data = {"id": badge.id, "slug": badge.slug, "title": badge.title, "description": badge.description}
        if badge.id in earned_ids:
            data["owned"] = True
            earned.append(data)
        else:
            data["owned"] = False
            available.append(data)
    return earned, available

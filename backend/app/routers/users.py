from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app import deps
from app.models.core import ChatSession, Memory, SessionMessage, User
from app.schemas import auth as auth_schema

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=auth_schema.UserProfile)
def me(current_user: User = Depends(deps.get_current_user), session: Session = Depends(deps.get_db)) -> auth_schema.UserProfile:
    stats = auth_schema.UserStats(total_minutes=_estimate_minutes(session, current_user.id), badges=_count_badges(session, current_user.id), quests_completed=_count_quests(session, current_user.id))
    return auth_schema.UserProfile(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        locale=current_user.locale,
        is_email_verified=current_user.is_email_verified,
        stats=stats,
        preferences={"theme": "light", "text_size": "md"},
    )


@router.patch("/me", response_model=auth_schema.UserProfile)
def update_me(
    payload: auth_schema.UserUpdate,
    current_user: User = Depends(deps.get_current_user),
    session: Session = Depends(deps.get_db),
) -> auth_schema.UserProfile:
    if payload.display_name:
        current_user.display_name = payload.display_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.locale:
        current_user.locale = payload.locale
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return me(current_user=current_user, session=session)  # type: ignore[arg-type]


@router.get("/me/history", response_model=auth_schema.UserHistoryResponse)
def history(current_user: User = Depends(deps.get_current_user), session: Session = Depends(deps.get_db)) -> auth_schema.UserHistoryResponse:
    sessions = session.exec(select(ChatSession).where(ChatSession.user_id == current_user.id).order_by(ChatSession.last_message_at.desc()).limit(20)).all()
    items = []
    for chat in sessions:
        items.append(
            auth_schema.UserHistoryItem(
                session_id=chat.id,
                agent_id=chat.agent_id,
                topic=chat.topic or "",
                duration_minutes=5,
                updated_at=chat.last_message_at,
            )
        )
    return auth_schema.UserHistoryResponse(items=items, cursor=None)


def _estimate_minutes(session: Session, user_id: int) -> int:
    messages = session.exec(select(SessionMessage).join(ChatSession).where(ChatSession.user_id == user_id)).all()
    return len(messages) * 2


def _count_badges(session: Session, user_id: int) -> int:
    from app.models.core import UserBadge

    rows = session.exec(select(UserBadge).where(UserBadge.user_id == user_id)).all()
    return len(rows)


def _count_quests(session: Session, user_id: int) -> int:
    from app.models.core import UserQuest

    rows = session.exec(select(UserQuest).where(UserQuest.user_id == user_id, UserQuest.status == "completed")).all()
    return len(rows)

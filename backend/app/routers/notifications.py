from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import deps
from app.schemas.notifications import NotificationList
from app.services import notifications as notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationList)
def list_notifications(current_user=Depends(deps.get_current_user), session: Session = Depends(deps.get_db)):
    items = notification_service.list_notifications(session, current_user.id)
    return NotificationList(items=items)


@router.post("/{notification_id}/read")
def mark_notification(notification_id: int, current_user=Depends(deps.get_current_user), session: Session = Depends(deps.get_db)):
    notification_service.mark_read(session, current_user.id, notification_id)
    return {"status": "ok"}

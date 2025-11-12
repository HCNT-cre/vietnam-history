from datetime import datetime

from sqlmodel import Session, select

from app.models.core import Notification, UserNotification


def seed_notifications(session: Session) -> None:
    if session.exec(select(Notification)).first():
        return
    notifications = [
        Notification(title="Chào mừng đến VietSaga", body="Bắt đầu đặt câu hỏi để mở khoá quest đầu tiên!", category="system"),
    ]
    session.add_all(notifications)
    session.commit()


def list_notifications(session: Session, user_id: int) -> list[dict]:
    seed_notifications(session)
    rows = session.exec(
        select(UserNotification).where(UserNotification.user_id == user_id)
    ).all()
    if not rows:
        notify = session.exec(select(Notification)).all()
        for base in notify:
            user_note = UserNotification(notification_id=base.id, user_id=user_id, is_read=False)
            session.add(user_note)
        session.commit()
        rows = session.exec(select(UserNotification).where(UserNotification.user_id == user_id)).all()
    result = []
    for row in rows:
        notification = session.get(Notification, row.notification_id)
        if notification:
            result.append(
                {
                    "id": row.id,
                    "title": notification.title,
                    "body": notification.body,
                    "category": notification.category,
                    "is_read": row.is_read,
                    "created_at": row.created_at,
                }
            )
    return result


def mark_read(session: Session, user_id: int, notification_id: int) -> None:
    row = session.exec(
        select(UserNotification).where(
            UserNotification.user_id == user_id,
            UserNotification.id == notification_id,
        )
    ).first()
    if row:
        row.is_read = True
        row.created_at = datetime.utcnow()
        session.add(row)
        session.commit()

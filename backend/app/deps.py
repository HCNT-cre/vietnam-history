from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.models.core import User
from app.services import auth as auth_service


def get_db() -> Session:
    with get_session() as session:
        yield session


def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    session: Session = Depends(get_db),
) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    token = authorization.split(" ", 1)[1]
    return auth_service.get_current_user(session, token)

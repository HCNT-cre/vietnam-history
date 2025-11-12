from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from jose import JWTError
from sqlmodel import Session, select

from app.config import get_settings
from app.models.core import RefreshToken, User
from app.utils.security import create_token, decode_token, hash_password, verify_password

settings = get_settings()


def register_user(session: Session, email: str, password: str, display_name: str, locale: str) -> User:
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=400, detail="email_in_use")
    user = User(email=email, hashed_password=hash_password(password), display_name=display_name, locale=locale)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account_locked")
    return user


def create_token_pair(session: Session, user: User) -> dict:
    access_token, _ = create_token(str(user.id), settings.access_token_expires, {"role": user.role})
    refresh_token, jti = create_token(str(user.id), settings.refresh_token_expires, {"type": "refresh"})
    refresh = RefreshToken(
        user_id=user.id,
        jti=jti,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.refresh_token_expires),
    )
    session.add(refresh)
    session.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.access_token_expires,
    }


def revoke_refresh_token(session: Session, jti: str) -> None:
    token = session.exec(select(RefreshToken).where(RefreshToken.jti == jti)).first()
    if token:
        token.revoked = True
        session.add(token)
        session.commit()


def refresh_tokens(session: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except JWTError as exc:  # pragma: no cover
        raise HTTPException(status_code=401, detail="invalid_token") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="invalid_token")
    jti = payload.get("jti")
    token_row = session.exec(select(RefreshToken).where(RefreshToken.jti == jti)).first()
    if not token_row or token_row.revoked:
        raise HTTPException(status_code=401, detail="token_reused")
    if token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="token_expired")
    token_row.revoked = True
    session.add(token_row)
    user = session.get(User, token_row.user_id)
    session.commit()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    return create_token_pair(session, user)


def get_current_user(session: Session, token: str) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid_token") from exc
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    return user

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app import deps
from app.models.core import User
from app.schemas import auth as auth_schema
from app.services import auth as auth_service
from app.utils.security import decode_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=auth_schema.RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: auth_schema.RegisterRequest, session: Session = Depends(deps.get_db)) -> auth_schema.RegisterResponse:
    user = auth_service.register_user(session, payload.email, payload.password, payload.display_name, payload.locale)
    return auth_schema.RegisterResponse(user_id=user.id, requires_email_verification=True)


@router.post("/login", response_model=auth_schema.TokenResponse)
def login(payload: auth_schema.LoginRequest, session: Session = Depends(deps.get_db)) -> auth_schema.TokenResponse:
    user = auth_service.authenticate_user(session, payload.email, payload.password)
    tokens = auth_service.create_token_pair(session, user)
    return auth_schema.TokenResponse(user=_to_public_user(user), **tokens)


@router.post("/token/refresh", response_model=auth_schema.TokenResponse)
def refresh(payload: auth_schema.RefreshRequest, session: Session = Depends(deps.get_db)) -> auth_schema.TokenResponse:
    tokens = auth_service.refresh_tokens(session, payload.refresh_token)
    user = session.get(User, int(decode_token(tokens["access_token"])["sub"]))
    assert user is not None
    return auth_schema.TokenResponse(user=_to_public_user(user), **tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(payload: auth_schema.LogoutRequest, session: Session = Depends(deps.get_db)) -> Response:
    if not payload.refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token_required")
    payload_data = decode_token(payload.refresh_token)
    auth_service.revoke_refresh_token(session, payload_data.get("jti"))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/reset/request", status_code=status.HTTP_200_OK)
def request_reset(payload: auth_schema.PasswordResetRequest) -> dict:
    # Stub: thực tế sẽ gửi email. Ở đây chỉ xác nhận đã nhận yêu cầu.
    return {"message": "Đã gửi email đặt lại mật khẩu (giả lập)."}


@router.post("/password/reset/confirm", status_code=status.HTTP_200_OK)
def confirm_reset(payload: auth_schema.PasswordResetConfirm) -> dict:
    # Stub: cần implement lưu token vào DB, đối chiếu, cập nhật mật khẩu.
    return {"message": "Đổi mật khẩu thành công (stub)."}


def _to_public_user(user) -> auth_schema.UserPublic:
    return auth_schema.UserPublic(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        locale=user.locale,
        is_email_verified=user.is_email_verified,
    )

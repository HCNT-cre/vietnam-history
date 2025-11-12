from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import get_settings
from app.services.rag import rag_service

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()


@router.get("/rag/health")
def rag_health(x_admin_token: str = Header(..., alias="X-Admin-Token")):
    if x_admin_token != settings.jwt_secret:
        raise HTTPException(status_code=401, detail="unauthorized")
    return rag_service.health()


@router.post("/rag/reindex")
def rag_reindex(x_admin_token: str = Header(..., alias="X-Admin-Token")):
    if x_admin_token != settings.jwt_secret:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"status": "queued"}

from fastapi import APIRouter, Depends

from app import deps
from app.schemas.content import SearchRequest, SearchResponse
from app.services.rag import rag_service

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
def search(payload: SearchRequest) -> SearchResponse:
    docs = rag_service.retrieve(payload.query, top_k=payload.top_k, filters=payload.filters)
    return SearchResponse(docs=docs)

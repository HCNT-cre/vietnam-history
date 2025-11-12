from __future__ import annotations

import logging
import uuid

import orjson
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app import deps
from app.config import get_settings
from app.db import init_db
from app.models.core import User
from app.routers import admin, auth, chat, library, memory, notifications, quests, search, timeline, users

settings = get_settings()

app = FastAPI(
    title="VietSaga API",
    default_response_class=ORJSONResponse,
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    logging.getLogger("vietsaga").info(
        "request",
        extra={
            "trace_id": trace_id,
            "path": request.url.path,
            "status": response.status_code,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    return response


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/healthz")
def health_check():
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(timeline.router, prefix=settings.api_prefix)
app.include_router(library.router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(quests.router, prefix=settings.api_prefix)
app.include_router(memory.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)

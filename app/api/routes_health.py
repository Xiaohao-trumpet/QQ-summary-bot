from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "environment": settings.app_env,
        "llm_enabled": settings.llm_enabled,
        "message_source": settings.message_source,
    }


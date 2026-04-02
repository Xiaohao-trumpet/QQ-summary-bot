from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.storage.repositories import BotRepository


router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
def list_messages(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    with request.app.state.database.session() as session:
        repository = BotRepository(session)
        rows = repository.list_recent_messages(limit=limit)
    return [
        {
            "message": item.message.model_dump(mode="json"),
            "analysis": item.analysis.model_dump(mode="json"),
        }
        for item in rows
    ]


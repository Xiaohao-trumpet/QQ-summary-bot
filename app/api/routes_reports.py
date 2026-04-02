from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request

from app.storage.repositories import BotRepository


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    with request.app.state.database.session() as session:
        repository = BotRepository(session)
        rows = repository.list_reports(limit=limit)
    return repository.serialize_report_rows(rows)


@router.get("/{report_id}")
def get_report(request: Request, report_id: str) -> dict:
    with request.app.state.database.session() as session:
        repository = BotRepository(session)
        row = repository.get_report(report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    return {
        "report_id": row.report_id,
        "window_start": row.window_start.isoformat(),
        "window_end": row.window_end.isoformat(),
        "summary_markdown": row.summary_markdown,
        "summary_json": json.loads(row.summary_json),
        "important_count": row.important_count,
        "critical_count": row.critical_count,
        "created_at": row.created_at.isoformat(),
    }

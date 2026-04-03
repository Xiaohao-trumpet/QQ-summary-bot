from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse

from app.config import PROJECT_ROOT


router = APIRouter(tags=["mobile"])
STATIC_DIR = PROJECT_ROOT / "app" / "ui" / "static"


@router.get("/mobile", response_class=HTMLResponse)
def mobile_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/mobile/manifest.webmanifest")
def mobile_manifest() -> FileResponse:
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@router.get("/mobile/sw.js")
def mobile_service_worker() -> FileResponse:
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@router.get("/mobile/icon.svg")
def mobile_icon() -> FileResponse:
    return FileResponse(STATIC_DIR / "icon.svg", media_type="image/svg+xml")


@router.get("/api/v1/mobile/feed")
def mobile_feed(request: Request) -> dict:
    return request.app.state.mobile_service.build_feed().model_dump(mode="json")


@router.get("/api/v1/mobile/reports")
def mobile_reports(request: Request, limit: int = Query(default=30, ge=1, le=100)) -> list[dict]:
    return request.app.state.mobile_service.list_reports(limit=limit)


@router.get("/api/v1/mobile/reports/{report_id}")
def mobile_report_detail(request: Request, report_id: str) -> dict:
    payload = request.app.state.mobile_service.get_report(report_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="report not found")
    return payload


@router.get("/api/v1/mobile/alerts")
def mobile_alerts(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return request.app.state.mobile_service.list_alerts(limit=limit)


@router.get("/api/v1/mobile/search")
def mobile_search(
    request: Request,
    q: str = Query(min_length=1),
    group_name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return request.app.state.mobile_service.search_messages(query=q, group_name=group_name, limit=limit)

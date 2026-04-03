from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from app.schemas import CollectorHeartbeatRequest, CollectorIngestRequest


router = APIRouter(prefix="/api/v1/collector", tags=["collector"])


def _validate_collector_token(request: Request, authorization: str | None) -> None:
    settings = request.app.state.settings
    expected_token = settings.collector_shared_token
    if not expected_token:
        raise HTTPException(status_code=503, detail="collector token is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected_token:
        raise HTTPException(status_code=403, detail="invalid collector token")


@router.post("/events")
async def ingest_collector_events(
    request: Request,
    payload: CollectorIngestRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _validate_collector_token(request, authorization)
    collector_service = request.app.state.collector_service
    result = await collector_service.ingest_events(payload)
    return result.model_dump(mode="json")


@router.post("/heartbeat")
def collector_heartbeat(
    request: Request,
    payload: CollectorHeartbeatRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _validate_collector_token(request, authorization)
    collector_service = request.app.state.collector_service
    return collector_service.heartbeat(payload.device)

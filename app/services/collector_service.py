from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from app.schemas import (
    CollectorDeviceInfo,
    CollectorEventPayload,
    CollectorIngestRequest,
    CollectorIngestResponse,
    RawQQMessage,
)
from app.storage.repositories import BotRepository


class CollectorService:
    def __init__(self, database, ingest_service) -> None:
        self.database = database
        self.ingest_service = ingest_service

    async def ingest_events(self, request: CollectorIngestRequest) -> CollectorIngestResponse:
        accepted_events = 0
        ignored_events = 0
        duplicate_events = 0

        raw_messages: list[RawQQMessage] = []
        accepted_event_ids: set[str] = set()

        with self.database.session() as session:
            repository = BotRepository(session)
            repository.upsert_device(
                device_id=request.device.device_id,
                device_name=request.device.device_name,
                platform=request.device.platform,
                app_version=request.device.app_version,
                status="online",
                seen_at=datetime.utcnow(),
                event_at=max((event.timestamp.replace(tzinfo=None) for event in request.events), default=None),
            )
            for event in request.events:
                if repository.collector_event_exists(event.event_id):
                    duplicate_events += 1
                    continue
                raw_message = self._to_raw_message(request.device, event)
                raw_messages.append(raw_message)
                accepted_event_ids.add(event.event_id)
                accepted_events += 1

        ingested_items = await self.ingest_service.ingest_messages(raw_messages)
        ingested_ids = {item.message.message_id for item in ingested_items}

        with self.database.session() as session:
            repository = BotRepository(session)
            for event in request.events:
                if event.event_id not in accepted_event_ids:
                    continue
                raw_message = self._to_raw_message(request.device, event)
                status = "ingested" if raw_message.message_id in ingested_ids else "duplicate"
                if status == "duplicate":
                    ignored_events += 1
                repository.save_collector_event(
                    event_id=event.event_id,
                    device_id=request.device.device_id,
                    source_type=event.source_type,
                    source_app=event.source_app,
                    group_name=event.group_name,
                    sender_name=event.sender_name,
                    content=event.content,
                    timestamp=event.timestamp.replace(tzinfo=None),
                    raw_title=event.raw_title,
                    raw_text=event.raw_text,
                    raw_subtext=event.raw_subtext,
                    mentioned_me=event.mentioned_me,
                    metadata=event.metadata,
                    message_id=raw_message.message_id,
                    status=status,
                )
            repository.upsert_device(
                device_id=request.device.device_id,
                device_name=request.device.device_name,
                platform=request.device.platform,
                app_version=request.device.app_version,
                status="online",
                seen_at=datetime.utcnow(),
                event_at=max((event.timestamp.replace(tzinfo=None) for event in request.events), default=None),
            )

        return CollectorIngestResponse(
            device_id=request.device.device_id,
            accepted_events=accepted_events,
            ingested_messages=len(ingested_items),
            duplicate_events=duplicate_events,
            ignored_events=ignored_events,
        )

    def heartbeat(self, device: CollectorDeviceInfo) -> dict:
        with self.database.session() as session:
            repository = BotRepository(session)
            repository.upsert_device(
                device_id=device.device_id,
                device_name=device.device_name,
                platform=device.platform,
                app_version=device.app_version,
                status="online",
                seen_at=datetime.utcnow(),
                event_at=None,
            )
        return {"status": "ok", "device_id": device.device_id}

    @staticmethod
    def _to_raw_message(device: CollectorDeviceInfo, event: CollectorEventPayload) -> RawQQMessage:
        normalized_group = event.group_name.strip()
        normalized_sender = event.sender_name.strip() or "未知发送人"
        message_id = hashlib.sha1(
            f"{normalized_group}|{normalized_sender}|{event.content.strip()}|{event.timestamp.isoformat()}".encode(
                "utf-8"
            )
        ).hexdigest()
        group_id = str(uuid.uuid5(uuid.NAMESPACE_URL, normalized_group))
        sender_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{normalized_group}:{normalized_sender}"))
        metadata = {
            "device_id": device.device_id,
            "device_name": device.device_name,
            "platform": device.platform,
            "app_version": device.app_version,
            "event_id": event.event_id,
            "source_type": event.source_type,
            "source_app": event.source_app,
            "raw_title": event.raw_title,
            "raw_text": event.raw_text,
            "raw_subtext": event.raw_subtext,
            **event.metadata,
        }
        return RawQQMessage(
            message_id=message_id,
            group_id=group_id,
            group_name=normalized_group,
            sender_id=sender_id,
            sender_name=normalized_sender,
            timestamp=event.timestamp,
            content=event.content,
            mentioned_me=event.mentioned_me,
            message_type="text",
            metadata=metadata,
        )

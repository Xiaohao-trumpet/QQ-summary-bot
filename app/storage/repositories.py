from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.schemas import HourlySummaryResult, MessageAnalysis, MessageWithAnalysis, NormalizedMessage
from app.storage.models import (
    AlertORM,
    CollectorEventORM,
    DeviceORM,
    HourlyReportORM,
    MessageAnalysisORM,
    MessageORM,
)


def _json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str):
    return json.loads(value) if value else []


class BotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def message_exists(self, dedup_hash: str) -> bool:
        stmt = select(MessageORM.id).where(MessageORM.dedup_hash == dedup_hash)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def save_message(self, message: NormalizedMessage) -> None:
        row = MessageORM(
            id=message.message_id,
            group_id=message.group_id,
            group_name=message.group_name,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            timestamp=message.timestamp,
            content=message.content,
            normalized_content=message.normalized_content,
            mentioned_me=message.mentioned_me,
            is_text=message.is_text,
            dedup_hash=message.dedup_hash,
            metadata_json=_json_dump(message.metadata),
        )
        self.session.add(row)

    def save_analysis(self, analysis: MessageAnalysis) -> None:
        row = MessageAnalysisORM(
            message_id=analysis.message_id,
            keyword_hits_json=_json_dump(analysis.keyword_hits),
            topic_tags_json=_json_dump(analysis.topic_tags),
            rule_score=analysis.rule_score,
            baoyan_relevance=analysis.baoyan_relevance,
            priority=analysis.priority,
            category=analysis.category,
            teacher_signal=analysis.teacher_signal,
            urgent_signal=analysis.urgent_signal,
            action_signal=analysis.action_signal,
            deadline_text=analysis.deadline_text,
            deadline_iso=analysis.deadline_iso,
            action_items_json=_json_dump(analysis.action_items),
            entities_json=_json_dump(analysis.entities),
            reason=analysis.reason,
            model_name=analysis.model_name,
            created_at=analysis.created_at,
        )
        self.session.merge(row)

    def save_alert(self, alert_id: str, message_id: str, channel: str, status: str, payload: str) -> None:
        row = AlertORM(
            alert_id=alert_id,
            message_id=message_id,
            channel=channel,
            status=status,
            payload=payload,
        )
        self.session.add(row)

    def collector_event_exists(self, event_id: str) -> bool:
        stmt = select(CollectorEventORM.event_id).where(CollectorEventORM.event_id == event_id)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def upsert_device(
        self,
        device_id: str,
        device_name: str,
        platform: str,
        app_version: str,
        status: str,
        seen_at: datetime,
        event_at: datetime | None = None,
    ) -> None:
        existing = self.session.get(DeviceORM, device_id)
        if existing is None:
            existing = DeviceORM(
                device_id=device_id,
                device_name=device_name,
                platform=platform,
                app_version=app_version,
                status=status,
                last_seen_at=seen_at,
                last_event_at=event_at,
                created_at=seen_at,
                updated_at=seen_at,
            )
            self.session.add(existing)
            return
        existing.device_name = device_name
        existing.platform = platform
        existing.app_version = app_version
        existing.status = status
        existing.last_seen_at = seen_at
        if event_at is not None:
            existing.last_event_at = event_at
        existing.updated_at = seen_at

    def save_collector_event(
        self,
        event_id: str,
        device_id: str,
        source_type: str,
        source_app: str,
        group_name: str,
        sender_name: str,
        content: str,
        timestamp: datetime,
        raw_title: str,
        raw_text: str,
        raw_subtext: str,
        mentioned_me: bool,
        metadata: dict,
        message_id: str,
        status: str,
    ) -> None:
        row = CollectorEventORM(
            event_id=event_id,
            device_id=device_id,
            source_type=source_type,
            source_app=source_app,
            group_name=group_name,
            sender_name=sender_name,
            content=content,
            timestamp=timestamp,
            raw_title=raw_title,
            raw_text=raw_text,
            raw_subtext=raw_subtext,
            mentioned_me=mentioned_me,
            metadata_json=_json_dump(metadata),
            message_id=message_id,
            status=status,
        )
        self.session.add(row)

    def save_report(
        self,
        report_id: str,
        report: HourlySummaryResult,
        important_count: int,
        critical_count: int,
    ) -> None:
        row = HourlyReportORM(
            report_id=report_id,
            window_start=report.window_start,
            window_end=report.window_end,
            summary_markdown=report.markdown,
            summary_json=_json_dump(report.summary_json.model_dump(mode="json")),
            important_count=important_count,
            critical_count=critical_count,
        )
        self.session.add(row)

    def list_messages_between(self, start, end) -> list[NormalizedMessage]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.timestamp >= start, MessageORM.timestamp <= end)
            .order_by(MessageORM.timestamp.asc())
        )
        return [self._to_message(row) for row in self.session.scalars(stmt).all()]

    def list_message_views_between(self, start, end) -> list[MessageWithAnalysis]:
        stmt: Select = (
            select(MessageORM, MessageAnalysisORM)
            .join(MessageAnalysisORM, MessageORM.id == MessageAnalysisORM.message_id, isouter=True)
            .where(MessageORM.timestamp >= start, MessageORM.timestamp <= end)
            .order_by(MessageORM.timestamp.asc())
        )
        items: list[MessageWithAnalysis] = []
        for message_row, analysis_row in self.session.execute(stmt).all():
            if analysis_row is None:
                continue
            items.append(
                MessageWithAnalysis(
                    message=self._to_message(message_row),
                    analysis=self._to_analysis(analysis_row),
                )
            )
        return items

    def list_recent_messages(self, limit: int = 50) -> list[MessageWithAnalysis]:
        stmt: Select = (
            select(MessageORM, MessageAnalysisORM)
            .join(MessageAnalysisORM, MessageORM.id == MessageAnalysisORM.message_id, isouter=True)
            .order_by(MessageORM.timestamp.desc())
            .limit(limit)
        )
        results: list[MessageWithAnalysis] = []
        for message_row, analysis_row in self.session.execute(stmt).all():
            if analysis_row is None:
                continue
            results.append(
                MessageWithAnalysis(
                    message=self._to_message(message_row),
                    analysis=self._to_analysis(analysis_row),
                )
            )
        return results

    def list_reports(self, limit: int = 20) -> list[HourlyReportORM]:
        stmt = select(HourlyReportORM).order_by(HourlyReportORM.window_end.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_latest_report(self) -> HourlyReportORM | None:
        stmt = select(HourlyReportORM).order_by(HourlyReportORM.window_end.desc()).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_report(self, report_id: str) -> HourlyReportORM | None:
        stmt = select(HourlyReportORM).where(HourlyReportORM.report_id == report_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_recent_alerts(self, limit: int = 20) -> list[AlertORM]:
        stmt = select(AlertORM).order_by(AlertORM.sent_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_devices(self) -> list[DeviceORM]:
        stmt = select(DeviceORM).order_by(DeviceORM.last_seen_at.desc())
        return list(self.session.scalars(stmt).all())

    def search_message_views(
        self,
        query: str,
        group_name: str | None = None,
        limit: int = 50,
    ) -> list[MessageWithAnalysis]:
        stmt: Select = (
            select(MessageORM, MessageAnalysisORM)
            .join(MessageAnalysisORM, MessageORM.id == MessageAnalysisORM.message_id, isouter=True)
            .where(
                or_(
                    MessageORM.normalized_content.contains(query),
                    MessageORM.group_name.contains(query),
                    MessageORM.sender_name.contains(query),
                )
            )
            .order_by(MessageORM.timestamp.desc())
            .limit(limit)
        )
        if group_name:
            stmt = stmt.where(MessageORM.group_name == group_name)
        results: list[MessageWithAnalysis] = []
        for message_row, analysis_row in self.session.execute(stmt).all():
            if analysis_row is None:
                continue
            results.append(
                MessageWithAnalysis(
                    message=self._to_message(message_row),
                    analysis=self._to_analysis(analysis_row),
                )
            )
        return results

    @staticmethod
    def _to_message(row: MessageORM) -> NormalizedMessage:
        return NormalizedMessage(
            message_id=row.id,
            group_id=row.group_id,
            group_name=row.group_name,
            sender_id=row.sender_id,
            sender_name=row.sender_name,
            timestamp=row.timestamp,
            content=row.content,
            normalized_content=row.normalized_content,
            mentioned_me=row.mentioned_me,
            is_text=row.is_text,
            dedup_hash=row.dedup_hash,
            metadata=json.loads(row.metadata_json or "{}"),
        )

    @staticmethod
    def _to_analysis(row: MessageAnalysisORM) -> MessageAnalysis:
        return MessageAnalysis(
            message_id=row.message_id,
            keyword_hits=_json_loads(row.keyword_hits_json),
            topic_tags=_json_loads(row.topic_tags_json),
            rule_score=row.rule_score,
            baoyan_relevance=row.baoyan_relevance,
            priority=row.priority,
            category=row.category,
            teacher_signal=row.teacher_signal,
            urgent_signal=row.urgent_signal,
            action_signal=row.action_signal,
            deadline_text=row.deadline_text,
            deadline_iso=row.deadline_iso,
            action_items=_json_loads(row.action_items_json),
            entities=_json_loads(row.entities_json),
            reason=row.reason,
            model_name=row.model_name,
            created_at=row.created_at,
        )

    @staticmethod
    def serialize_report_rows(rows: Iterable[HourlyReportORM]) -> list[dict]:
        payload: list[dict] = []
        for row in rows:
            payload.append(
                {
                    "report_id": row.report_id,
                    "window_start": row.window_start.isoformat(),
                    "window_end": row.window_end.isoformat(),
                    "important_count": row.important_count,
                    "critical_count": row.critical_count,
                    "created_at": row.created_at.isoformat(),
                }
            )
        return payload

    @staticmethod
    def serialize_report(row: HourlyReportORM) -> dict:
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

    @staticmethod
    def serialize_alert_rows(rows: Iterable[AlertORM]) -> list[dict]:
        return [
            {
                "alert_id": row.alert_id,
                "message_id": row.message_id,
                "channel": row.channel,
                "status": row.status,
                "sent_at": row.sent_at.isoformat(),
                "payload": row.payload,
            }
            for row in rows
        ]

    @staticmethod
    def serialize_device_rows(rows: Iterable[DeviceORM], stale_after_seconds: int = 600) -> list[dict]:
        now = datetime.utcnow()
        payload: list[dict] = []
        for row in rows:
            last_seen = row.last_seen_at
            active = (now - last_seen).total_seconds() <= stale_after_seconds if last_seen else False
            payload.append(
                {
                    "device_id": row.device_id,
                    "device_name": row.device_name,
                    "platform": row.platform,
                    "app_version": row.app_version,
                    "status": "online" if active else row.status,
                    "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else "",
                    "last_event_at": row.last_event_at.isoformat() if row.last_event_at else "",
                }
            )
        return payload

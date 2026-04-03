from __future__ import annotations

from datetime import datetime

from app.schemas import MobileFeedResponse
from app.storage.repositories import BotRepository


class MobileService:
    def __init__(self, database) -> None:
        self.database = database

    def build_feed(self) -> MobileFeedResponse:
        with self.database.session() as session:
            repository = BotRepository(session)
            latest_report = repository.get_latest_report()
            alerts = repository.list_recent_alerts(limit=20)
            devices = repository.list_devices()

        latest_report_payload = repository.serialize_report(latest_report) if latest_report else None
        today_todos: list[str] = []
        group_overview: list[dict] = []
        if latest_report_payload:
            summary_json = latest_report_payload["summary_json"]
            today_todos = summary_json.get("todos", [])
            group_overview = summary_json.get("group_briefs", [])

        return MobileFeedResponse(
            generated_at=datetime.now().astimezone().isoformat(),
            latest_report=latest_report_payload,
            recent_alerts=repository.serialize_alert_rows(alerts),
            devices=repository.serialize_device_rows(devices),
            today_todos=today_todos,
            group_overview=group_overview,
        )

    def list_reports(self, limit: int = 30) -> list[dict]:
        with self.database.session() as session:
            repository = BotRepository(session)
            rows = repository.list_reports(limit=limit)
        return repository.serialize_report_rows(rows)

    def get_report(self, report_id: str) -> dict | None:
        with self.database.session() as session:
            repository = BotRepository(session)
            row = repository.get_report(report_id)
        if row is None:
            return None
        return repository.serialize_report(row)

    def list_alerts(self, limit: int = 50) -> list[dict]:
        with self.database.session() as session:
            repository = BotRepository(session)
            rows = repository.list_recent_alerts(limit=limit)
        return repository.serialize_alert_rows(rows)

    def search_messages(self, query: str, group_name: str | None = None, limit: int = 50) -> list[dict]:
        with self.database.session() as session:
            repository = BotRepository(session)
            rows = repository.search_message_views(query=query, group_name=group_name, limit=limit)
        return [
            {
                "message": item.message.model_dump(mode="json"),
                "analysis": item.analysis.model_dump(mode="json"),
            }
            for item in rows
        ]

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from app.storage.repositories import BotRepository


class ReportService:
    def __init__(self, database, summarizer, clusterer) -> None:
        self.database = database
        self.summarizer = summarizer
        self.clusterer = clusterer

    async def generate_hourly_report(
        self,
        window_end: datetime | None = None,
        window_seconds: int = 3600,
    ):
        end = window_end or datetime.now()
        start = end - timedelta(seconds=window_seconds)
        with self.database.session() as session:
            repository = BotRepository(session)
            messages = repository.list_message_views_between(start, end)
        clusters = self.clusterer.cluster(messages)
        report = await self.summarizer.summarize(start, end, messages, clusters)
        important_count = len(report.summary_json.important_items)
        critical_count = sum(1 for item in messages if item.analysis.priority == "critical")
        with self.database.session() as session:
            repository = BotRepository(session)
            repository.save_report(
                report_id=str(uuid.uuid4()),
                report=report,
                important_count=important_count,
                critical_count=critical_count,
            )
        return report


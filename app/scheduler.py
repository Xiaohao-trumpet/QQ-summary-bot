from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler


LOGGER = logging.getLogger(__name__)


class BotScheduler:
    def __init__(self, settings, collector, ingest_service, report_service) -> None:
        self.settings = settings
        self.collector = collector
        self.ingest_service = ingest_service
        self.report_service = report_service
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        if self.collector is not None:
            self.scheduler.add_job(
                self.poll_messages,
                "interval",
                seconds=self.settings.poll_interval_seconds,
                id="poll_messages",
                replace_existing=True,
            )
        self.scheduler.add_job(
            self.generate_report,
            "interval",
            seconds=self.settings.hourly_summary_interval_seconds,
            id="generate_hourly_report",
            replace_existing=True,
        )
        self.scheduler.start()
        self._started = True
        LOGGER.info("scheduler started")

    def shutdown(self) -> None:
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False
            LOGGER.info("scheduler stopped")

    async def poll_messages(self) -> None:
        if self.collector is None:
            return
        messages = await self.collector.poll()
        if not messages:
            return
        ingested = await self.ingest_service.ingest_messages(messages)
        LOGGER.info("ingested %s messages from scheduler", len(ingested))

    async def generate_report(self) -> None:
        report = await self.report_service.generate_hourly_report(window_end=datetime.now())
        LOGGER.info("generated hourly report %s", report.window_end.isoformat())

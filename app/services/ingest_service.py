from __future__ import annotations

from app.schemas import MessageWithAnalysis, RawQQMessage
from app.storage.repositories import BotRepository


class IngestService:
    def __init__(self, database, normalizer, analysis_service, alert_manager) -> None:
        self.database = database
        self.normalizer = normalizer
        self.analysis_service = analysis_service
        self.alert_manager = alert_manager

    async def ingest_messages(self, raw_messages: list[RawQQMessage]) -> list[MessageWithAnalysis]:
        ingested: list[MessageWithAnalysis] = []
        with self.database.session() as session:
            repository = BotRepository(session)
            for raw_message in raw_messages:
                normalized = self.normalizer.normalize(raw_message)
                if normalized is None:
                    continue
                if repository.message_exists(normalized.dedup_hash):
                    continue
                analysis = await self.analysis_service.analyze_message(normalized)
                repository.save_message(normalized)
                repository.save_analysis(analysis)
                item = MessageWithAnalysis(message=normalized, analysis=analysis)
                self.alert_manager.dispatch(item, repository)
                ingested.append(item)
        return ingested


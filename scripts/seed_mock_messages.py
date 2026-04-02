from __future__ import annotations

import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.collector.file_replay_collector import FileReplayCollector
from app.config import get_settings
from app.pipeline.alerting import AlertManager
from app.pipeline.classifier import MessageClassifier
from app.pipeline.normalizer import MessageNormalizer
from app.pipeline.rule_engine import RuleEngine
from app.services.analysis_service import AnalysisService
from app.services.ingest_service import IngestService
from app.storage.db import Database


async def run() -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    database.create_all()
    classifier = MessageClassifier(
        llm_client=None,
        llm_model_name="rules-only",
        llm_temperature=settings.openai_temperature,
        llm_rule_threshold=settings.classifier_llm_rule_threshold,
        critical_rule_threshold=settings.classifier_critical_rule_threshold,
        high_rule_threshold=settings.classifier_high_rule_threshold,
    )
    analysis_service = AnalysisService(
        rule_engine=RuleEngine.from_path(settings.keyword_rules_path),
        classifier=classifier,
    )
    ingest_service = IngestService(
        database=database,
        normalizer=MessageNormalizer(),
        analysis_service=analysis_service,
        alert_manager=AlertManager(settings.alert_channel_list),
    )
    collector = FileReplayCollector(settings.message_source_path)
    ingested = await ingest_service.ingest_messages(await collector.poll())
    print(f"seeded {len(ingested)} messages into {settings.database_url}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()


from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.collector.file_replay_collector import FileReplayCollector
from app.config import get_settings
from app.llm.client import OpenAICompatClient
from app.pipeline.alerting import AlertManager
from app.pipeline.classifier import MessageClassifier
from app.pipeline.clusterer import MessageClusterer
from app.pipeline.normalizer import MessageNormalizer
from app.pipeline.rule_engine import RuleEngine
from app.pipeline.summarizer import HourlySummarizer
from app.services.analysis_service import AnalysisService
from app.services.ingest_service import IngestService
from app.services.report_service import ReportService
from app.storage.db import Database


async def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    database = Database(settings.database_url)
    database.create_all()

    llm_client = None
    if settings.llm_enabled:
        llm_client = OpenAICompatClient(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries,
        )

    rule_engine = RuleEngine.from_path(settings.keyword_rules_path)
    classifier = MessageClassifier(
        llm_client=llm_client,
        llm_model_name=settings.openai_model or "rules-only",
        llm_temperature=settings.openai_temperature,
        llm_rule_threshold=settings.classifier_llm_rule_threshold,
        critical_rule_threshold=settings.classifier_critical_rule_threshold,
        high_rule_threshold=settings.classifier_high_rule_threshold,
    )
    analysis_service = AnalysisService(rule_engine=rule_engine, classifier=classifier)
    ingest_service = IngestService(
        database=database,
        normalizer=MessageNormalizer(),
        analysis_service=analysis_service,
        alert_manager=AlertManager(settings.alert_channel_list),
    )
    report_service = ReportService(
        database=database,
        summarizer=HourlySummarizer(
            llm_client=llm_client,
            llm_model_name=settings.openai_model or "rules-only",
            llm_temperature=settings.openai_temperature,
        ),
        clusterer=MessageClusterer(),
    )

    collector = FileReplayCollector(settings.message_source_path)
    raw_messages = await collector.poll()
    ingested = await ingest_service.ingest_messages(raw_messages)
    latest_timestamp = max((item.message.timestamp for item in ingested), default=None)
    report = await report_service.generate_hourly_report(window_end=latest_timestamp)

    print(f"Ingested {len(ingested)} messages")
    print()
    print(report.markdown)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()


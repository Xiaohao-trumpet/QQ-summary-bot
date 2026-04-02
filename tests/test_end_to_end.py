from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from app.pipeline.alerting import AlertManager
from app.pipeline.classifier import MessageClassifier
from app.pipeline.clusterer import MessageClusterer
from app.pipeline.normalizer import MessageNormalizer
from app.pipeline.rule_engine import RuleEngine
from app.pipeline.summarizer import HourlySummarizer
from app.schemas import RawQQMessage
from app.services.analysis_service import AnalysisService
from app.services.ingest_service import IngestService
from app.services.report_service import ReportService
from app.storage.db import Database
from app.storage.repositories import BotRepository


def test_end_to_end_pipeline(tmp_path: Path):
    database = Database(f"sqlite:///{tmp_path / 'test.db'}")
    database.create_all()
    classifier = MessageClassifier(
        llm_client=None,
        llm_model_name="rules-only",
        llm_temperature=0.1,
        llm_rule_threshold=2.5,
        critical_rule_threshold=8.5,
        high_rule_threshold=6.0,
    )
    analysis_service = AnalysisService(RuleEngine(), classifier)
    ingest_service = IngestService(
        database=database,
        normalizer=MessageNormalizer(),
        analysis_service=analysis_service,
        alert_manager=AlertManager(["console"]),
    )
    report_service = ReportService(
        database=database,
        summarizer=HourlySummarizer(llm_client=None, llm_model_name="rules-only", llm_temperature=0.1),
        clusterer=MessageClusterer(),
    )

    raw_messages = [
        RawQQMessage(
            message_id="m1",
            group_id="g1",
            group_name="保研群",
            sender_id="u1",
            sender_name="李老师",
            timestamp=datetime.fromisoformat("2026-04-02T19:00:00+08:00"),
            content="今晚24点前提交预推免材料。",
        ),
        RawQQMessage(
            message_id="m2",
            group_id="g1",
            group_name="保研群",
            sender_id="u2",
            sender_name="管理员",
            timestamp=datetime.fromisoformat("2026-04-02T19:10:00+08:00"),
            content="明早9点机试，记得签到。",
        ),
    ]

    ingested = asyncio.run(ingest_service.ingest_messages(raw_messages))
    report = asyncio.run(
        report_service.generate_hourly_report(
            window_end=datetime.fromisoformat("2026-04-02T20:00:00+08:00")
        )
    )

    with database.session() as session:
        repository = BotRepository(session)
        saved_messages = repository.list_recent_messages(limit=10)

    assert len(ingested) == 2
    assert len(saved_messages) == 2
    assert report.summary_json.important_items


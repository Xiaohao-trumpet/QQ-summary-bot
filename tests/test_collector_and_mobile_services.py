from __future__ import annotations

import asyncio
from datetime import datetime

from app.pipeline.alerting import AlertManager
from app.pipeline.classifier import MessageClassifier
from app.pipeline.clusterer import MessageClusterer
from app.pipeline.normalizer import MessageNormalizer
from app.pipeline.rule_engine import RuleEngine
from app.pipeline.summarizer import HourlySummarizer
from app.schemas import CollectorDeviceInfo, CollectorEventPayload, CollectorIngestRequest
from app.services.analysis_service import AnalysisService
from app.services.collector_service import CollectorService
from app.services.ingest_service import IngestService
from app.services.mobile_service import MobileService
from app.services.report_service import ReportService
from app.storage.db import Database


def test_collector_service_ingests_and_mobile_feed_reads(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'collector_services.db'}")
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
    collector_service = CollectorService(database=database, ingest_service=ingest_service)
    mobile_service = MobileService(database=database)
    report_service = ReportService(
        database=database,
        summarizer=HourlySummarizer(llm_client=None, llm_model_name="rules-only", llm_temperature=0.1),
        clusterer=MessageClusterer(),
    )

    result = asyncio.run(
        collector_service.ingest_events(
            CollectorIngestRequest(
                device=CollectorDeviceInfo(
                    device_id="android-001",
                    device_name="Pixel 9",
                    platform="android",
                    app_version="0.1.0",
                ),
                events=[
                    CollectorEventPayload(
                        event_id="evt-001",
                        source_type="android_notification",
                        source_app="com.tencent.mobileqq",
                        group_name="清华软院预推免群",
                        sender_name="李老师",
                        content="今晚24点前提交预推免意向表和成绩单",
                        timestamp="2026-04-03T10:05:23+08:00",
                        mentioned_me=False,
                        raw_title="清华软院预推免群",
                        raw_text="李老师: 今晚24点前提交预推免意向表和成绩单",
                        raw_subtext="",
                    )
                ],
            )
        )
    )

    assert result.accepted_events == 1
    assert result.ingested_messages == 1

    asyncio.run(
        report_service.generate_hourly_report(
            window_end=datetime.fromisoformat("2026-04-03T11:00:00+08:00")
        )
    )
    feed = mobile_service.build_feed()
    search_results = mobile_service.search_messages(query="预推免")

    assert feed.devices
    assert feed.devices[0].device_id == "android-001"
    assert search_results
    assert search_results[0]["message"]["group_name"] == "清华软院预推免群"

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes_collector import router as collector_router
from app.api.routes_health import router as health_router
from app.api.routes_messages import router as messages_router
from app.api.routes_mobile import router as mobile_router
from app.api.routes_reports import router as reports_router
from app.collector.file_replay_collector import FileReplayCollector
from app.collector.mock_collector import MockCollector
from app.collector.qq_notification_collector import QQNotificationCollector
from app.config import get_settings
from app.llm.client import OpenAICompatClient
from app.pipeline.alerting import AlertManager
from app.pipeline.classifier import MessageClassifier
from app.pipeline.clusterer import MessageClusterer
from app.pipeline.normalizer import MessageNormalizer
from app.pipeline.rule_engine import RuleEngine
from app.pipeline.summarizer import HourlySummarizer
from app.scheduler import BotScheduler
from app.services.analysis_service import AnalysisService
from app.services.collector_service import CollectorService
from app.services.ingest_service import IngestService
from app.services.mobile_service import MobileService
from app.services.report_service import ReportService
from app.storage.db import Database
from app.config import PROJECT_ROOT


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_collector(source: str, source_path: str):
    if source == "file":
        return FileReplayCollector(source_path)
    if source == "mock":
        return MockCollector([])
    if source == "qq_notification":
        settings = get_settings()
        return QQNotificationCollector(
            allowed_groups=settings.qq_allowed_group_list,
            group_filter_mode=settings.qq_group_filter_mode,
            app_names=settings.qq_notification_app_name_list,
            capture_private_chats=settings.qq_capture_private_chats,
        )
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
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
    normalizer = MessageNormalizer()
    analysis_service = AnalysisService(rule_engine=rule_engine, classifier=classifier)
    alert_manager = AlertManager(settings.alert_channel_list)
    summarizer = HourlySummarizer(
        llm_client=llm_client,
        llm_model_name=settings.openai_model or "rules-only",
        llm_temperature=settings.openai_temperature,
    )
    report_service = ReportService(
        database=database,
        summarizer=summarizer,
        clusterer=MessageClusterer(),
    )
    collector = build_collector(settings.message_source, str(settings.message_source_path))
    ingest_service = IngestService(
        database=database,
        normalizer=normalizer,
        analysis_service=analysis_service,
        alert_manager=alert_manager,
    )
    collector_service = CollectorService(database=database, ingest_service=ingest_service)
    mobile_service = MobileService(database=database)

    scheduler = BotScheduler(
        settings=settings,
        collector=collector,
        ingest_service=ingest_service,
        report_service=report_service,
    )

    app.state.settings = settings
    app.state.database = database
    app.state.collector = collector
    app.state.ingest_service = ingest_service
    app.state.collector_service = collector_service
    app.state.mobile_service = mobile_service
    app.state.report_service = report_service
    app.state.scheduler = scheduler

    if settings.enable_scheduler:
        scheduler.start()

    yield

    if settings.enable_scheduler:
        scheduler.shutdown()

    if collector is not None:
        await collector.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Summary Bot", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(messages_router)
    app.include_router(reports_router)
    app.include_router(collector_router)
    app.include_router(mobile_router)
    app.mount(
        "/mobile-assets",
        StaticFiles(directory=PROJECT_ROOT / "app" / "ui" / "static"),
        name="mobile-assets",
    )
    return app


app = create_app()

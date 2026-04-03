from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MessageORM(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[str] = mapped_column(Text, index=True)
    group_name: Mapped[str] = mapped_column(Text, index=True)
    sender_id: Mapped[str] = mapped_column(Text, index=True)
    sender_name: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    content: Mapped[str] = mapped_column(Text)
    normalized_content: Mapped[str] = mapped_column(Text)
    mentioned_me: Mapped[bool] = mapped_column(Boolean, default=False)
    is_text: Mapped[bool] = mapped_column(Boolean, default=True)
    dedup_hash: Mapped[str] = mapped_column(Text, unique=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MessageAnalysisORM(Base):
    __tablename__ = "message_analysis"

    message_id: Mapped[str] = mapped_column(Text, primary_key=True)
    keyword_hits_json: Mapped[str] = mapped_column(Text, default="[]")
    topic_tags_json: Mapped[str] = mapped_column(Text, default="[]")
    rule_score: Mapped[float] = mapped_column(Float, default=0.0)
    baoyan_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[str] = mapped_column(Text, index=True)
    category: Mapped[str] = mapped_column(Text, index=True)
    teacher_signal: Mapped[bool] = mapped_column(Boolean, default=False)
    urgent_signal: Mapped[bool] = mapped_column(Boolean, default=False)
    action_signal: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline_text: Mapped[str] = mapped_column(Text, default="")
    deadline_iso: Mapped[str] = mapped_column(Text, default="")
    action_items_json: Mapped[str] = mapped_column(Text, default="[]")
    entities_json: Mapped[str] = mapped_column(Text, default="[]")
    reason: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HourlyReportORM(Base):
    __tablename__ = "hourly_reports"

    report_id: Mapped[str] = mapped_column(Text, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime, index=True)
    summary_markdown: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str] = mapped_column(Text)
    important_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertORM(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(Text, primary_key=True)
    message_id: Mapped[str] = mapped_column(Text, index=True)
    channel: Mapped[str] = mapped_column(Text, index=True)
    status: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    payload: Mapped[str] = mapped_column(Text)


class DeviceORM(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(Text, primary_key=True)
    device_name: Mapped[str] = mapped_column(Text, index=True)
    platform: Mapped[str] = mapped_column(Text, index=True)
    app_version: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(Text, default="unknown")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CollectorEventORM(Base):
    __tablename__ = "collector_events"

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    device_id: Mapped[str] = mapped_column(Text, index=True)
    source_type: Mapped[str] = mapped_column(Text, index=True)
    source_app: Mapped[str] = mapped_column(Text, default="")
    group_name: Mapped[str] = mapped_column(Text, index=True)
    sender_name: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    raw_title: Mapped[str] = mapped_column(Text, default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    raw_subtext: Mapped[str] = mapped_column(Text, default="")
    mentioned_me: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    message_id: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(Text, default="received", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

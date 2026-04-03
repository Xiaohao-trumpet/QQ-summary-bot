from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Priority = Literal["critical", "high", "medium", "low", "ignore"]
Category = Literal[
    "teacher_info",
    "application_notice",
    "deadline",
    "interview_exam",
    "mentor_contact",
    "internship_group",
    "offer_waitlist",
    "policy_info",
    "rumor_unverified",
    "chat_noise",
    "irrelevant",
]


class RawQQMessage(BaseModel):
    message_id: str
    group_id: str
    group_name: str
    sender_id: str
    sender_name: str
    timestamp: datetime
    content: str
    mentioned_me: bool = False
    message_type: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedMessage(RawQQMessage):
    normalized_content: str
    is_text: bool = True
    dedup_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuleSignal(BaseModel):
    keyword_hits: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)
    rule_score: float = 0.0
    teacher_signal: bool = False
    urgent_signal: bool = False
    action_signal: bool = False
    needs_llm: bool = False


class MessageClassification(BaseModel):
    baoyan_relevance: float = Field(ge=0.0, le=1.0)
    priority: Priority
    category: Category
    teacher_signal: bool = False
    urgent_signal: bool = False
    action_signal: bool = False
    deadline_text: str = ""
    deadline_iso: str = ""
    entities: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    reason: str


class MessageAnalysis(BaseModel):
    message_id: str
    keyword_hits: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)
    rule_score: float = 0.0
    baoyan_relevance: float = Field(ge=0.0, le=1.0)
    priority: Priority
    category: Category
    teacher_signal: bool = False
    urgent_signal: bool = False
    action_signal: bool = False
    deadline_text: str = ""
    deadline_iso: str = ""
    action_items: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    reason: str
    model_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageWithAnalysis(BaseModel):
    message: NormalizedMessage
    analysis: MessageAnalysis


class MessageCluster(BaseModel):
    cluster_id: str
    group_name: str
    category: Category
    priority: Priority
    source_message_ids: list[str] = Field(default_factory=list)
    representative_messages: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    summary_hint: str = ""


class SummaryImportantItem(BaseModel):
    title: str
    priority: Literal["critical", "high", "medium"]
    category: str
    summary: str
    source_message_ids: list[str] = Field(default_factory=list)
    action_required: bool = False
    action_items: list[str] = Field(default_factory=list)


class GroupBrief(BaseModel):
    group_name: str
    brief: str
    noise_level: Literal["high", "medium", "low"]


class HourlySummaryPayload(BaseModel):
    important_items: list[SummaryImportantItem] = Field(default_factory=list)
    todos: list[str] = Field(default_factory=list)
    deadlines: list[str] = Field(default_factory=list)
    teacher_updates: list[str] = Field(default_factory=list)
    rumors: list[str] = Field(default_factory=list)
    group_briefs: list[GroupBrief] = Field(default_factory=list)


class HourlySummaryResult(BaseModel):
    window_start: datetime
    window_end: datetime
    markdown: str
    summary_json: HourlySummaryPayload


class CollectorDeviceInfo(BaseModel):
    device_id: str
    device_name: str
    platform: str
    app_version: str = ""


class CollectorEventPayload(BaseModel):
    event_id: str
    source_type: str
    source_app: str
    group_name: str
    sender_name: str
    content: str
    timestamp: datetime
    mentioned_me: bool = False
    raw_title: str = ""
    raw_text: str = ""
    raw_subtext: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectorIngestRequest(BaseModel):
    device: CollectorDeviceInfo
    events: list[CollectorEventPayload] = Field(default_factory=list)


class CollectorIngestResponse(BaseModel):
    device_id: str
    accepted_events: int
    ingested_messages: int
    duplicate_events: int
    ignored_events: int


class CollectorHeartbeatRequest(BaseModel):
    device: CollectorDeviceInfo


class MobileDeviceStatus(BaseModel):
    device_id: str
    device_name: str
    platform: str
    app_version: str = ""
    status: str
    last_seen_at: str = ""
    last_event_at: str = ""


class MobileAlertItem(BaseModel):
    alert_id: str
    message_id: str
    channel: str
    status: str
    sent_at: str
    payload: str


class MobileReportItem(BaseModel):
    report_id: str
    window_start: str
    window_end: str
    summary_markdown: str
    summary_json: dict[str, Any]
    important_count: int
    critical_count: int
    created_at: str


class MobileFeedResponse(BaseModel):
    generated_at: str
    latest_report: MobileReportItem | None = None
    recent_alerts: list[MobileAlertItem] = Field(default_factory=list)
    devices: list[MobileDeviceStatus] = Field(default_factory=list)
    today_todos: list[str] = Field(default_factory=list)
    group_overview: list[dict[str, Any]] = Field(default_factory=list)


class SearchResultItem(BaseModel):
    message: dict[str, Any]
    analysis: dict[str, Any]

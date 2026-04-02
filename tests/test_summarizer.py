from __future__ import annotations

import asyncio
from datetime import datetime

from app.pipeline.clusterer import MessageClusterer
from app.pipeline.summarizer import HourlySummarizer
from app.schemas import MessageAnalysis, MessageWithAnalysis, NormalizedMessage


def build_item(message_id: str, content: str, priority: str, category: str) -> MessageWithAnalysis:
    message = NormalizedMessage(
        message_id=message_id,
        group_id="g1",
        group_name="测试群",
        sender_id="u1",
        sender_name="李老师",
        timestamp=datetime.fromisoformat("2026-04-02T19:00:00+08:00"),
        content=content,
        normalized_content=content,
        mentioned_me=False,
        dedup_hash=message_id,
    )
    analysis = MessageAnalysis(
        message_id=message_id,
        keyword_hits=["预推免"],
        topic_tags=[category],
        rule_score=8.0,
        baoyan_relevance=0.9,
        priority=priority,
        category=category,
        teacher_signal=True,
        urgent_signal=True,
        action_signal=True,
        deadline_text="今晚24点前",
        deadline_iso="",
        action_items=["提交"],
        entities=["李老师"],
        reason="老师通知",
        model_name="rules-only",
    )
    return MessageWithAnalysis(message=message, analysis=analysis)


def test_summarizer_generates_markdown_and_json():
    items = [
        build_item("m1", "今晚24点前提交材料", "critical", "deadline"),
        build_item("m2", "明早9点机试", "high", "interview_exam"),
    ]
    clusters = MessageClusterer().cluster(items)
    summarizer = HourlySummarizer(llm_client=None, llm_model_name="rules-only", llm_temperature=0.1)

    result = asyncio.run(
        summarizer.summarize(
            window_start=datetime.fromisoformat("2026-04-02T19:00:00+08:00"),
            window_end=datetime.fromisoformat("2026-04-02T20:00:00+08:00"),
            messages=items,
            clusters=clusters,
        )
    )

    assert "# 保研小时简报" in result.markdown
    assert result.summary_json.important_items
    assert result.summary_json.deadlines


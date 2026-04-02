from __future__ import annotations

import asyncio
from datetime import datetime

from app.pipeline.classifier import MessageClassifier
from app.pipeline.normalizer import MessageNormalizer
from app.pipeline.rule_engine import RuleEngine
from app.schemas import RawQQMessage


def test_classifier_returns_high_priority_for_urgent_notice():
    raw = RawQQMessage(
        message_id="3",
        group_id="g1",
        group_name="保研群",
        sender_id="u1",
        sender_name="管理员",
        timestamp=datetime.fromisoformat("2026-04-02T19:00:00+08:00"),
        content="明早9点机试，8:40前签到并检查设备。",
        mentioned_me=True,
    )
    message = MessageNormalizer().normalize(raw)
    signal = RuleEngine().analyze(message)
    classifier = MessageClassifier(
        llm_client=None,
        llm_model_name="rules-only",
        llm_temperature=0.1,
        llm_rule_threshold=2.5,
        critical_rule_threshold=8.5,
        high_rule_threshold=6.0,
    )

    analysis = asyncio.run(classifier.classify(message, signal))

    assert analysis.priority in {"high", "critical"}
    assert analysis.category == "interview_exam"
    assert analysis.urgent_signal is True


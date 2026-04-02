from __future__ import annotations

from datetime import datetime

from app.pipeline.normalizer import MessageNormalizer
from app.pipeline.rule_engine import RuleEngine
from app.schemas import RawQQMessage


def test_rule_engine_flags_teacher_deadline_and_action():
    raw = RawQQMessage(
        message_id="2",
        group_id="g1",
        group_name="预推免群",
        sender_id="u1",
        sender_name="李老师",
        timestamp=datetime.fromisoformat("2026-04-02T19:00:00+08:00"),
        content="今晚10点前提交预推免材料，尽快填写表单。",
    )
    message = MessageNormalizer().normalize(raw)
    signal = RuleEngine().analyze(message)

    assert signal.teacher_signal is True
    assert signal.urgent_signal is True
    assert signal.action_signal is True
    assert signal.rule_score >= 6.0
    assert "预推免" in signal.keyword_hits


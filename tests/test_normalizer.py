from __future__ import annotations

from datetime import datetime

from app.pipeline.normalizer import MessageNormalizer
from app.schemas import RawQQMessage


def test_normalizer_rewrites_deadline_and_taoci_terms():
    raw = RawQQMessage(
        message_id="1",
        group_id="g1",
        group_name="保研群",
        sender_id="u1",
        sender_name="群友",
        timestamp=datetime.fromisoformat("2026-04-02T19:00:00+08:00"),
        content="保研陶瓷导师 ddl 今晚要发邮件",
    )

    normalized = MessageNormalizer().normalize(raw)

    assert normalized is not None
    assert "套磁" in normalized.normalized_content
    assert "截止" in normalized.normalized_content
    assert normalized.dedup_hash


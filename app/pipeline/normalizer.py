from __future__ import annotations

import re
import unicodedata

from app.pipeline.dedup import MessageDeduplicator
from app.schemas import NormalizedMessage, RawQQMessage


BAOYAN_CONTEXT_WORDS = {
    "保研",
    "推免",
    "预推免",
    "夏令营",
    "导师",
    "老师",
    "实验室",
    "套磁",
    "联系导师",
    "面试",
    "机试",
    "进组",
}

SPACE_RE = re.compile(r"\s+")


class MessageNormalizer:
    def normalize(self, raw_message: RawQQMessage) -> NormalizedMessage | None:
        if raw_message.message_type != "text":
            return None
        content = unicodedata.normalize("NFKC", raw_message.content or "")
        content = SPACE_RE.sub(" ", content).strip()
        if not content:
            return None

        normalized = content
        normalized = normalized.replace("DDL", "截止").replace("ddl", "截止")
        normalized = normalized.replace("deadline", "截止").replace("Deadline", "截止")
        normalized = normalized.replace("预推免系统", "预推免 系统")

        if any(word in normalized for word in BAOYAN_CONTEXT_WORDS):
            normalized = normalized.replace("套瓷", "套磁").replace("陶瓷", "套磁")

        dedup_hash = MessageDeduplicator.build_hash(raw_message, normalized)
        return NormalizedMessage(
            message_id=raw_message.message_id,
            group_id=raw_message.group_id,
            group_name=raw_message.group_name,
            sender_id=raw_message.sender_id,
            sender_name=raw_message.sender_name,
            timestamp=raw_message.timestamp,
            content=raw_message.content,
            normalized_content=normalized,
            mentioned_me=raw_message.mentioned_me,
            is_text=True,
            dedup_hash=dedup_hash,
            metadata=dict(raw_message.metadata),
        )

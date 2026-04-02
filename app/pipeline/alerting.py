from __future__ import annotations

import logging
import uuid

from app.schemas import MessageWithAnalysis


LOGGER = logging.getLogger(__name__)

PRIORITY_SCORE = {"ignore": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class AlertManager:
    def __init__(self, channels: list[str]) -> None:
        self.channels = channels or ["console"]

    def should_alert(self, item: MessageWithAnalysis) -> bool:
        if item.message.mentioned_me:
            return True
        if PRIORITY_SCORE[item.analysis.priority] >= PRIORITY_SCORE["high"]:
            return True
        return item.analysis.teacher_signal and item.analysis.baoyan_relevance >= 0.7

    def dispatch(self, item: MessageWithAnalysis, repository) -> None:
        if not self.should_alert(item):
            return
        payload = self._build_payload(item)
        for channel in self.channels:
            if channel == "console":
                LOGGER.warning(payload)
                status = "printed"
            else:
                status = "skipped"
            repository.save_alert(
                alert_id=str(uuid.uuid4()),
                message_id=item.message.message_id,
                channel=channel,
                status=status,
                payload=payload,
            )

    @staticmethod
    def _build_payload(item: MessageWithAnalysis) -> str:
        return (
            "[高优先级保研消息]\n"
            f"群：{item.message.group_name}\n"
            f"发送人：{item.message.sender_name}\n"
            f"时间：{item.message.timestamp.isoformat()}\n\n"
            f"原文：\n{item.message.normalized_content}\n\n"
            f"判断：\n"
            f"- 相关性：{item.analysis.baoyan_relevance:.2f}\n"
            f"- 类别：{item.analysis.category}\n"
            f"- 优先级：{item.analysis.priority}\n"
            f"- 原因：{item.analysis.reason}\n\n"
            f"建议动作：{', '.join(item.analysis.action_items) if item.analysis.action_items else '检查原文并决定是否跟进'}"
        )


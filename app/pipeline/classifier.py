from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import ValidationError

from app.llm.prompts import MESSAGE_CLASSIFIER_SYSTEM_PROMPT, build_classifier_user_prompt
from app.llm.schemas import LLMMessageClassification
from app.schemas import MessageAnalysis, MessageClassification, MessageWithAnalysis, NormalizedMessage, RuleSignal


LOGGER = logging.getLogger(__name__)

PRIORITY_ORDER = {
    "ignore": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

CATEGORY_PRIORITY_MAP = {
    "deadline": "deadline",
    "interview_exam": "interview_exam",
    "mentor_contact": "mentor_contact",
    "teacher_info": "teacher_info",
    "offer_waitlist": "offer_waitlist",
    "application_notice": "application_notice",
    "internship_group": "internship_group",
    "policy_info": "policy_info",
    "rumor_unverified": "rumor_unverified",
}

CATEGORY_INFERENCE_ORDER = [
    "interview_exam",
    "mentor_contact",
    "offer_waitlist",
    "deadline",
    "teacher_info",
    "application_notice",
    "internship_group",
    "policy_info",
    "rumor_unverified",
]

ENTITY_PATTERNS = [
    re.compile(r"[\u4e00-\u9fff]{2,20}(大学|学院|实验室|研究院|课题组)"),
    re.compile(r"[\u4e00-\u9fff]{2,8}老师"),
]


class MessageClassifier:
    def __init__(
        self,
        llm_client,
        llm_model_name: str,
        llm_temperature: float,
        llm_rule_threshold: float,
        critical_rule_threshold: float,
        high_rule_threshold: float,
    ) -> None:
        self.llm_client = llm_client
        self.llm_model_name = llm_model_name
        self.llm_temperature = llm_temperature
        self.llm_rule_threshold = llm_rule_threshold
        self.critical_rule_threshold = critical_rule_threshold
        self.high_rule_threshold = high_rule_threshold

    async def classify(self, message: NormalizedMessage, rule_signal: RuleSignal) -> MessageAnalysis:
        baseline = self._rule_based_classification(message, rule_signal)
        final_classification = baseline
        model_name = "rules-only"

        if self._should_use_llm(message, rule_signal):
            temp_view = MessageWithAnalysis(
                message=message,
                analysis=MessageAnalysis(
                    message_id=message.message_id,
                    keyword_hits=rule_signal.keyword_hits,
                    topic_tags=rule_signal.topic_tags,
                    rule_score=rule_signal.rule_score,
                    baoyan_relevance=baseline.baoyan_relevance,
                    priority=baseline.priority,
                    category=baseline.category,
                    teacher_signal=baseline.teacher_signal,
                    urgent_signal=baseline.urgent_signal,
                    action_signal=baseline.action_signal,
                    deadline_text=baseline.deadline_text,
                    deadline_iso=baseline.deadline_iso,
                    action_items=baseline.action_items,
                    entities=baseline.entities,
                    reason=baseline.reason,
                    model_name="rules-only",
                ),
            )
            try:
                llm_payload = await self.llm_client.chat_json(
                    system_prompt=MESSAGE_CLASSIFIER_SYSTEM_PROMPT,
                    user_prompt=build_classifier_user_prompt(temp_view),
                    schema=LLMMessageClassification.model_json_schema(),
                    temperature=self.llm_temperature,
                )
                llm_classification = LLMMessageClassification.model_validate(llm_payload)
                final_classification = self._merge_classifications(baseline, llm_classification)
                model_name = self.llm_model_name
            except (RuntimeError, ValidationError, ValueError) as exc:
                LOGGER.warning("falling back to rule-based classification: %s", exc)

        return MessageAnalysis(
            message_id=message.message_id,
            keyword_hits=rule_signal.keyword_hits,
            topic_tags=rule_signal.topic_tags,
            rule_score=rule_signal.rule_score,
            baoyan_relevance=final_classification.baoyan_relevance,
            priority=final_classification.priority,
            category=final_classification.category,
            teacher_signal=final_classification.teacher_signal,
            urgent_signal=final_classification.urgent_signal,
            action_signal=final_classification.action_signal,
            deadline_text=final_classification.deadline_text,
            deadline_iso=final_classification.deadline_iso,
            action_items=final_classification.action_items,
            entities=final_classification.entities,
            reason=final_classification.reason,
            model_name=model_name,
        )

    def _should_use_llm(self, message: NormalizedMessage, rule_signal: RuleSignal) -> bool:
        if self.llm_client is None:
            return False
        return (
            rule_signal.rule_score >= self.llm_rule_threshold
            or message.mentioned_me
            or rule_signal.teacher_signal
            or rule_signal.urgent_signal
        )

    def _rule_based_classification(
        self,
        message: NormalizedMessage,
        rule_signal: RuleSignal,
    ) -> MessageClassification:
        relevance = min(1.0, max(0.0, rule_signal.rule_score / 10.0))
        category = self._infer_category(rule_signal.topic_tags)
        priority = "low"
        if category == "irrelevant" and rule_signal.rule_score < 1.0:
            priority = "ignore"
        elif rule_signal.rule_score >= self.critical_rule_threshold or (
            rule_signal.urgent_signal and rule_signal.action_signal and rule_signal.teacher_signal
        ):
            priority = "critical"
        elif rule_signal.rule_score >= self.high_rule_threshold or (
            rule_signal.urgent_signal and rule_signal.action_signal
        ):
            priority = "high"
        elif rule_signal.rule_score >= 3.0:
            priority = "medium"

        if message.mentioned_me and priority in {"ignore", "low"}:
            priority = "medium"

        deadline_text = self._extract_deadline_text(message.normalized_content) if rule_signal.urgent_signal else ""
        action_items = self._extract_action_items(message.normalized_content)
        entities = self._extract_entities(message)
        reason_parts = []
        if rule_signal.teacher_signal:
            reason_parts.append("疑似老师/导师/官方角色消息")
        if rule_signal.urgent_signal:
            reason_parts.append("包含明确时间压力")
        if rule_signal.action_signal:
            reason_parts.append("包含行动要求")
        if not reason_parts:
            reason_parts.append("关键词命中显示与保研流程相关")

        return MessageClassification(
            baoyan_relevance=relevance,
            priority=priority,
            category=category,
            teacher_signal=rule_signal.teacher_signal,
            urgent_signal=rule_signal.urgent_signal,
            action_signal=rule_signal.action_signal,
            deadline_text=deadline_text,
            deadline_iso="",
            entities=entities,
            action_items=action_items,
            reason="；".join(reason_parts),
        )

    def _merge_classifications(
        self,
        baseline: MessageClassification,
        llm_classification: LLMMessageClassification,
    ) -> MessageClassification:
        priority = baseline.priority
        if PRIORITY_ORDER[llm_classification.priority] > PRIORITY_ORDER[baseline.priority]:
            priority = llm_classification.priority

        category = llm_classification.category
        if category == "irrelevant" and PRIORITY_ORDER[baseline.priority] >= PRIORITY_ORDER["medium"]:
            category = baseline.category

        reason = llm_classification.reason or baseline.reason
        if baseline.priority != llm_classification.priority:
            reason = f"{reason}；规则引擎已保守上调优先级" if PRIORITY_ORDER[baseline.priority] > PRIORITY_ORDER[llm_classification.priority] else reason

        return MessageClassification(
            baoyan_relevance=max(baseline.baoyan_relevance, llm_classification.baoyan_relevance),
            priority=priority,
            category=category,
            teacher_signal=baseline.teacher_signal or llm_classification.teacher_signal,
            urgent_signal=baseline.urgent_signal or llm_classification.urgent_signal,
            action_signal=baseline.action_signal or llm_classification.action_signal,
            deadline_text=llm_classification.deadline_text or baseline.deadline_text,
            deadline_iso=llm_classification.deadline_iso or baseline.deadline_iso,
            entities=sorted(set(baseline.entities + llm_classification.entities)),
            action_items=sorted(set(baseline.action_items + llm_classification.action_items)),
            reason=reason,
        )

    @staticmethod
    def _infer_category(topic_tags: list[str]) -> str:
        for tag in CATEGORY_INFERENCE_ORDER:
            if tag in topic_tags:
                return CATEGORY_PRIORITY_MAP[tag]
        for tag in topic_tags:
            if tag in CATEGORY_PRIORITY_MAP:
                return CATEGORY_PRIORITY_MAP[tag]
        if "baoyan" in topic_tags:
            return "policy_info"
        return "irrelevant"

    @staticmethod
    def _extract_deadline_text(text: str) -> str:
        matches = re.findall(r"(今晚|明早|明天|今天|周[一二三四五六日天])?\s*(\d{1,2}[:点时]\d{0,2})?\s*(前|截止)?", text)
        parts = ["".join(part for part in match if part) for match in matches if any(match)]
        return parts[0] if parts else ""

    @staticmethod
    def _extract_action_items(text: str) -> list[str]:
        phrases = []
        for keyword in ["提交", "填写", "确认", "发送邮件", "联系导师", "报名", "填表", "补交"]:
            if keyword in text:
                phrases.append(keyword)
        return phrases

    @staticmethod
    def _extract_entities(message: NormalizedMessage) -> list[str]:
        entities = []
        for pattern in ENTITY_PATTERNS:
            entities.extend(match.group(0) for match in pattern.finditer(message.normalized_content))
        if any(title in message.sender_name for title in ["老师", "导师", "教授"]):
            entities.append(message.sender_name)
        return sorted(set(entities))

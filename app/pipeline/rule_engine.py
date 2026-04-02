from __future__ import annotations

import json
import re
from pathlib import Path

from app.schemas import NormalizedMessage, RuleSignal


DEFAULT_RULES = {
    "strong_keywords": {
        "保研": 2.5,
        "推免": 2.5,
        "预推免": 2.7,
        "夏令营": 2.4,
        "补录": 2.7,
        "候补": 2.1,
        "递补": 2.1,
        "入营": 2.0,
        "优营": 2.0,
        "拟录取": 2.8,
        "offer": 1.8,
        "rank": 1.6,
        "bar": 1.2,
        "com": 1.2,
        "联系导师": 2.4,
        "套磁": 2.2,
        "机试": 2.3,
        "面试": 2.3,
        "复试": 2.0,
        "进组": 1.7,
        "实习": 1.4,
        "直博": 1.8,
    },
    "context_keywords": {
        "老师": 0.7,
        "导师": 0.8,
        "学院": 0.8,
        "实验室": 0.8,
        "研究院": 0.8,
        "课题组": 0.8,
        "招生": 1.0,
        "报名": 1.1,
        "申请": 1.0,
        "网申": 1.0,
        "材料": 0.9,
        "简历": 0.7,
        "成绩单": 0.7,
    },
    "urgent_keywords": {
        "截止": 2.0,
        "今晚": 1.8,
        "明早": 1.8,
        "尽快": 1.5,
        "马上": 1.3,
        "立刻": 1.3,
        "最后一天": 1.8,
        "24点前": 1.8,
        "速填": 1.6,
    },
    "action_keywords": {
        "提交": 1.4,
        "填写": 1.3,
        "确认": 1.1,
        "发送邮件": 1.4,
        "联系导师": 1.6,
        "报名": 1.2,
        "填表": 1.2,
        "补交": 1.4,
        "回复": 0.8,
        "查看": 0.4,
    },
    "noise_keywords": {
        "蹲": -0.5,
        "dd": -0.4,
        "顶": -0.4,
        "有人知道吗": -0.2,
        "求问": -0.3,
        "真的假的": -0.4,
    },
    "teacher_titles": [
        "老师",
        "导师",
        "教授",
        "研究员",
        "招生办",
        "教务",
        "管理员",
    ],
    "group_keywords": ["保研", "推免", "夏令营", "预推免", "实验室", "导师"],
    "category_keywords": {
        "teacher_info": ["老师", "导师", "学院", "实验室", "招生办"],
        "application_notice": ["报名", "网申", "申请", "材料", "系统开放", "系统关闭"],
        "deadline": ["截止", "今晚", "明早", "尽快", "最后一天"],
        "interview_exam": ["面试", "机试", "复试"],
        "mentor_contact": ["联系导师", "套磁", "导师回复", "陶瓷", "套瓷"],
        "internship_group": ["进组", "实习", "课题组"],
        "offer_waitlist": ["候补", "递补", "拟录取", "offer", "优营", "入营"],
        "policy_info": ["rank", "bar", "com", "政策"],
        "rumor_unverified": ["听说", "小道消息", "据说"],
    },
}

DEADLINE_PATTERN = re.compile(r"(今晚|明早|明天|今天|周[一二三四五六日天])?(\d{1,2}[:点时]\d{0,2})?")


class RuleEngine:
    def __init__(self, rules: dict | None = None) -> None:
        self.rules = rules or DEFAULT_RULES

    @classmethod
    def from_path(cls, path: str | Path) -> "RuleEngine":
        file_path = Path(path)
        if file_path.exists():
            with file_path.open("r", encoding="utf-8") as handle:
                return cls(json.load(handle))
        return cls()

    def analyze(self, message: NormalizedMessage) -> RuleSignal:
        text = message.normalized_content
        keyword_hits: list[str] = []
        topic_tags: set[str] = set()
        score = 0.0

        for keyword, weight in self.rules["strong_keywords"].items():
            if keyword.lower() in text.lower():
                keyword_hits.append(keyword)
                topic_tags.add("baoyan")
                score += weight

        for keyword, weight in self.rules["context_keywords"].items():
            if keyword in text:
                keyword_hits.append(keyword)
                score += weight

        teacher_signal = self._has_teacher_signal(message)
        if teacher_signal:
            topic_tags.add("teacher")
            score += 1.4

        urgent_signal = False
        for keyword, weight in self.rules["urgent_keywords"].items():
            if keyword in text:
                keyword_hits.append(keyword)
                topic_tags.add("deadline")
                urgent_signal = True
                score += weight

        if DEADLINE_PATTERN.search(text) and ("截止" in text or urgent_signal):
            urgent_signal = True
            topic_tags.add("deadline")

        action_signal = False
        for keyword, weight in self.rules["action_keywords"].items():
            if keyword in text:
                keyword_hits.append(keyword)
                topic_tags.add("action")
                action_signal = True
                score += weight

        for keyword, weight in self.rules["noise_keywords"].items():
            if keyword in text:
                score += weight

        if any(group_word in message.group_name for group_word in self.rules["group_keywords"]):
            score += 0.8
            topic_tags.add("group_context")

        if message.mentioned_me:
            score += 1.5
            topic_tags.add("mentioned_me")

        for category, keywords in self.rules["category_keywords"].items():
            if any(keyword in text for keyword in keywords):
                topic_tags.add(category)

        needs_llm = (
            score >= 2.5
            or teacher_signal
            or urgent_signal
            or action_signal
            or message.mentioned_me
        )
        return RuleSignal(
            keyword_hits=sorted(set(keyword_hits)),
            topic_tags=sorted(topic_tags),
            rule_score=round(score, 2),
            teacher_signal=teacher_signal,
            urgent_signal=urgent_signal,
            action_signal=action_signal,
            needs_llm=needs_llm,
        )

    def _has_teacher_signal(self, message: NormalizedMessage) -> bool:
        sender = message.sender_name
        text = message.normalized_content
        return any(title in sender or title in text for title in self.rules["teacher_titles"])


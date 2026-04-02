from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime

from pydantic import ValidationError

from app.llm.prompts import HOURLY_SUMMARY_SYSTEM_PROMPT, build_hourly_summary_user_prompt
from app.llm.schemas import LLMHourlySummaryPayload
from app.schemas import GroupBrief, HourlySummaryPayload, HourlySummaryResult, MessageCluster, MessageWithAnalysis, SummaryImportantItem


LOGGER = logging.getLogger(__name__)

PRIORITY_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1, "ignore": 0}


class HourlySummarizer:
    def __init__(self, llm_client, llm_model_name: str, llm_temperature: float) -> None:
        self.llm_client = llm_client
        self.llm_model_name = llm_model_name
        self.llm_temperature = llm_temperature

    async def summarize(
        self,
        window_start: datetime,
        window_end: datetime,
        messages: list[MessageWithAnalysis],
        clusters: list[MessageCluster],
    ) -> HourlySummaryResult:
        fallback_payload = self._build_fallback_payload(messages)
        summary_payload = fallback_payload

        important_messages = [
            {
                "message_id": item.message.message_id,
                "group_name": item.message.group_name,
                "sender_name": item.message.sender_name,
                "timestamp": item.message.timestamp.isoformat(),
                "content": item.message.normalized_content,
                "priority": item.analysis.priority,
                "category": item.analysis.category,
                "reason": item.analysis.reason,
                "action_items": item.analysis.action_items,
            }
            for item in messages
            if item.analysis.priority in {"critical", "high", "medium"}
        ]
        group_stats = self._group_stats(messages)
        high_count = sum(1 for item in messages if item.analysis.priority == "high")
        critical_count = sum(1 for item in messages if item.analysis.priority == "critical")

        if self.llm_client is not None and important_messages:
            try:
                llm_payload = await self.llm_client.chat_json(
                    system_prompt=HOURLY_SUMMARY_SYSTEM_PROMPT,
                    user_prompt=build_hourly_summary_user_prompt(
                        window_start=window_start.isoformat(),
                        window_end=window_end.isoformat(),
                        total_messages=len(messages),
                        high_count=high_count,
                        critical_count=critical_count,
                        important_messages_json=json.dumps(important_messages, ensure_ascii=False, indent=2),
                        clusters_json=json.dumps(
                            [cluster.model_dump(mode="json") for cluster in clusters],
                            ensure_ascii=False,
                            indent=2,
                        ),
                        group_stats_json=json.dumps(group_stats, ensure_ascii=False, indent=2),
                    ),
                    schema=LLMHourlySummaryPayload.model_json_schema(),
                    temperature=self.llm_temperature,
                )
                summary_payload = LLMHourlySummaryPayload.model_validate(llm_payload)
            except (RuntimeError, ValidationError, ValueError) as exc:
                LOGGER.warning("falling back to deterministic summarizer: %s", exc)

        markdown = self._render_markdown(summary_payload, window_start, window_end)
        return HourlySummaryResult(
            window_start=window_start,
            window_end=window_end,
            markdown=markdown,
            summary_json=summary_payload,
        )

    def _build_fallback_payload(self, messages: list[MessageWithAnalysis]) -> HourlySummaryPayload:
        sorted_messages = sorted(
            messages,
            key=lambda item: (
                PRIORITY_SCORE[item.analysis.priority],
                item.analysis.baoyan_relevance,
                item.message.timestamp.timestamp(),
            ),
            reverse=True,
        )
        important_items: list[SummaryImportantItem] = []
        todos: list[str] = []
        deadlines: list[str] = []
        teacher_updates: list[str] = []
        rumors: list[str] = []

        for item in sorted_messages:
            if item.analysis.priority in {"ignore", "low"}:
                continue
            if len(important_items) < 8 and item.analysis.priority in {"critical", "high", "medium"}:
                important_items.append(
                    SummaryImportantItem(
                        title=f"{item.message.group_name} / {item.analysis.category}",
                        priority=item.analysis.priority,
                        category=item.analysis.category,
                        summary=f"{item.message.sender_name}: {item.message.normalized_content[:120]}",
                        source_message_ids=[item.message.message_id],
                        action_required=bool(item.analysis.action_items),
                        action_items=item.analysis.action_items,
                    )
                )
            todos.extend(item.analysis.action_items)
            if item.analysis.deadline_text:
                deadlines.append(
                    f"{item.message.group_name}: {item.analysis.deadline_text} [{item.message.message_id}]"
                )
            if item.analysis.teacher_signal:
                teacher_updates.append(
                    f"{item.message.group_name}: {item.message.sender_name} - {item.message.normalized_content[:80]} [{item.message.message_id}]"
                )
            if item.analysis.category == "rumor_unverified":
                rumors.append(
                    f"{item.message.group_name}: {item.message.normalized_content[:80]} [{item.message.message_id}]"
                )

        group_briefs = [
            GroupBrief(
                group_name=group_name,
                brief=brief,
                noise_level=noise_level,
            )
            for group_name, brief, noise_level in self._build_group_briefs(messages)
        ]
        return HourlySummaryPayload(
            important_items=important_items,
            todos=sorted(set(todos)),
            deadlines=sorted(set(deadlines)),
            teacher_updates=teacher_updates[:10],
            rumors=rumors[:10],
            group_briefs=group_briefs,
        )

    @staticmethod
    def _group_stats(messages: list[MessageWithAnalysis]) -> list[dict]:
        grouped: dict[str, Counter] = defaultdict(Counter)
        for item in messages:
            grouped[item.message.group_name]["total"] += 1
            grouped[item.message.group_name][item.analysis.priority] += 1
            grouped[item.message.group_name][item.analysis.category] += 1
        payload = []
        for group_name, counter in grouped.items():
            payload.append({"group_name": group_name, "stats": dict(counter)})
        return payload

    @staticmethod
    def _build_group_briefs(messages: list[MessageWithAnalysis]) -> list[tuple[str, str, str]]:
        grouped: dict[str, list[MessageWithAnalysis]] = defaultdict(list)
        for item in messages:
            grouped[item.message.group_name].append(item)

        briefs: list[tuple[str, str, str]] = []
        for group_name, group_items in grouped.items():
            important = [item for item in group_items if item.analysis.priority in {"critical", "high", "medium"}]
            noise_ratio = 1.0 - (len(important) / len(group_items) if group_items else 1.0)
            if not important:
                brief = "噪声较多，无新增关键信息"
            else:
                top_item = max(important, key=lambda item: PRIORITY_SCORE[item.analysis.priority])
                brief = f"重点在 {top_item.analysis.category}: {top_item.message.normalized_content[:70]}"
            noise_level = "high" if noise_ratio > 0.7 else "medium" if noise_ratio > 0.35 else "low"
            briefs.append((group_name, brief, noise_level))
        return briefs

    @staticmethod
    def _render_markdown(
        payload: HourlySummaryPayload,
        window_start: datetime,
        window_end: datetime,
    ) -> str:
        lines = [
            "# 保研小时简报",
            f"时间窗口：{window_start.isoformat()} ~ {window_end.isoformat()}",
            "",
            "## 一、最重要的消息",
        ]
        if payload.important_items:
            lines.extend(f"- {item.summary} [{','.join(item.source_message_ids)}]" for item in payload.important_items)
        else:
            lines.append("- 本时间窗内没有新的高价值消息。")

        lines.extend(["", "## 二、老师/学院/实验室动态"])
        if payload.teacher_updates:
            lines.extend(f"- {item}" for item in payload.teacher_updates)
        else:
            lines.append("- 无新增老师/学院/实验室关键信息。")

        lines.extend(["", "## 三、截止时间与行动事项"])
        if payload.deadlines:
            lines.extend(f"- {item}" for item in payload.deadlines)
        else:
            lines.append("- 暂无明确截止时间。")
        if payload.todos:
            lines.extend(f"- 建议动作：{todo}" for todo in payload.todos)

        lines.extend(["", "## 四、面试/机试/联系导师/进组动态"])
        interview_related = [
            item.summary
            for item in payload.important_items
            if item.category in {"interview_exam", "mentor_contact", "internship_group"}
        ]
        if interview_related:
            lines.extend(f"- {item}" for item in interview_related)
        else:
            lines.append("- 暂无新增关键动态。")

        lines.extend(["", "## 五、待核实信息"])
        if payload.rumors:
            lines.extend(f"- {item}" for item in payload.rumors)
        else:
            lines.append("- 暂无待核实传闻。")

        lines.extend(["", "## 六、按群速览"])
        if payload.group_briefs:
            lines.extend(f"- {item.group_name}：{item.brief}" for item in payload.group_briefs)
        else:
            lines.append("- 当前没有群消息数据。")

        lines.extend(["", "## 七、建议下一步"])
        if payload.todos:
            lines.extend(f"- 优先处理：{todo}" for todo in payload.todos[:5])
        elif payload.deadlines:
            lines.append("- 检查所有明确截止项并确认是否需要提交材料。")
        else:
            lines.append("- 继续观察，无需立即动作。")
        return "\n".join(lines)


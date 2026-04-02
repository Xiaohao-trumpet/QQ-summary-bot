from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.llm.prompts import MESSAGE_CLASSIFIER_SYSTEM_PROMPT, build_classifier_user_prompt
from app.llm.schemas import LLMMessageClassification
from app.schemas import MessageAnalysis, MessageWithAnalysis, NormalizedMessage


async def main() -> None:
    settings = get_settings()
    message = MessageWithAnalysis(
        message=NormalizedMessage(
            message_id="debug-message",
            group_id="g1",
            group_name="清华软院预推免群",
            sender_id="u1",
            sender_name="李老师",
            timestamp="2026-04-02T19:05:00+08:00",
            content="今晚24点前提交预推免意向表、简历和成绩单，逾期视为放弃。",
            normalized_content="今晚24点前提交预推免意向表、简历和成绩单，逾期视为放弃。",
            mentioned_me=False,
            dedup_hash="debug-hash",
        ),
        analysis=MessageAnalysis(
            message_id="debug-message",
            keyword_hits=["预推免", "今晚", "提交"],
            topic_tags=["baoyan", "deadline", "action", "teacher_info"],
            rule_score=9.1,
            baoyan_relevance=0.91,
            priority="critical",
            category="deadline",
            teacher_signal=True,
            urgent_signal=True,
            action_signal=True,
            deadline_text="今晚24点前",
            deadline_iso="",
            action_items=["提交"],
            entities=["李老师"],
            reason="疑似老师/导师/官方角色消息；包含明确时间压力；包含行动要求",
            model_name="rules-only",
        ),
    )

    payload = {
        "model": settings.openai_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": MESSAGE_CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": build_classifier_user_prompt(message)},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "emit_message_classification",
                    "description": "Emit a structured baoyan message classification.",
                    "parameters": LLMMessageClassification.model_json_schema(),
                },
            }
        ],
        "tool_choice": "required",
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=settings.openai_timeout) as client:
        response = await client.post(
            f"{settings.openai_base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
    print(f"status={response.status_code}")
    print(response.text[:8000])
    parsed = response.json()
    print("parsed_keys=", sorted(parsed.keys()))
    choices = parsed.get("choices") or []
    if choices:
        print("first_choice=", json.dumps(choices[0], ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

from app.schemas import GroupBrief, HourlySummaryPayload, MessageClassification, SummaryImportantItem


class LLMMessageClassification(MessageClassification):
    pass


class LLMImportantItem(SummaryImportantItem):
    pass


class LLMGroupBrief(GroupBrief):
    pass


class LLMHourlySummaryPayload(HourlySummaryPayload):
    pass


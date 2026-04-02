from __future__ import annotations

from app.pipeline.classifier import MessageClassifier
from app.pipeline.rule_engine import RuleEngine
from app.schemas import MessageAnalysis, NormalizedMessage


class AnalysisService:
    def __init__(self, rule_engine: RuleEngine, classifier: MessageClassifier) -> None:
        self.rule_engine = rule_engine
        self.classifier = classifier

    async def analyze_message(self, message: NormalizedMessage) -> MessageAnalysis:
        rule_signal = self.rule_engine.analyze(message)
        return await self.classifier.classify(message, rule_signal)


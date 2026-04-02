from __future__ import annotations

from collections import deque
from typing import Iterable

from app.collector.base import BaseCollector
from app.schemas import RawQQMessage


class MockCollector(BaseCollector):
    def __init__(self, messages: Iterable[RawQQMessage]) -> None:
        self._messages = deque(messages)

    async def poll(self) -> list[RawQQMessage]:
        if not self._messages:
            return []
        batch: list[RawQQMessage] = []
        while self._messages:
            batch.append(self._messages.popleft())
        return batch


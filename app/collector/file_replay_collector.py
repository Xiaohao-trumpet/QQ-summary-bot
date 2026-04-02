from __future__ import annotations

import json
from pathlib import Path

from app.collector.base import BaseCollector
from app.schemas import RawQQMessage


class FileReplayCollector(BaseCollector):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._cursor = 0

    async def poll(self) -> list[RawQQMessage]:
        if not self.path.exists():
            return []
        messages: list[RawQQMessage] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle):
                if idx < self._cursor:
                    continue
                payload = json.loads(line)
                messages.append(RawQQMessage.model_validate(payload))
        self._cursor += len(messages)
        return messages


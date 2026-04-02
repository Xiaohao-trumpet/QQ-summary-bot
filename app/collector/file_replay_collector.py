from __future__ import annotations

import json
import logging
from pathlib import Path

from app.collector.base import BaseCollector
from app.schemas import RawQQMessage


LOGGER = logging.getLogger(__name__)


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
                stripped = line.strip()
                if not stripped:
                    LOGGER.debug("skip empty line %s in %s", idx + 1, self.path)
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON on line {idx + 1} of {self.path}: {exc.msg}"
                    ) from exc
                messages.append(RawQQMessage.model_validate(payload))
        self._cursor += len(messages)
        return messages

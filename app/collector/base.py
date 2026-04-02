from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import RawQQMessage


class BaseCollector(ABC):
    @abstractmethod
    async def poll(self) -> list[RawQQMessage]:
        """Return newly observed raw messages."""


from __future__ import annotations

import hashlib

from app.schemas import RawQQMessage


class MessageDeduplicator:
    @staticmethod
    def build_hash(message: RawQQMessage, normalized_content: str) -> str:
        minute_bucket = message.timestamp.replace(second=0, microsecond=0).isoformat()
        payload = "|".join(
            [
                message.group_id,
                message.sender_id,
                minute_bucket,
                normalized_content,
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()


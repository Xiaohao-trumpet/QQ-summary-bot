from __future__ import annotations

import hashlib
from collections import defaultdict

from app.llm.prompts import build_cluster_summary_hint
from app.schemas import MessageCluster, MessageWithAnalysis

PRIORITY_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1, "ignore": 0}


class MessageClusterer:
    def cluster(self, messages: list[MessageWithAnalysis]) -> list[MessageCluster]:
        buckets: dict[tuple[str, str, str], list[MessageWithAnalysis]] = defaultdict(list)
        for item in messages:
            if item.analysis.priority in {"ignore", "low"}:
                continue
            entity_key = item.analysis.entities[0] if item.analysis.entities else "general"
            key = (item.message.group_name, item.analysis.category, entity_key)
            buckets[key].append(item)

        clusters: list[MessageCluster] = []
        for (group_name, category, entity_key), items in buckets.items():
            sorted_items = sorted(
                items,
                key=lambda entry: entry.message.timestamp,
            )
            source_ids = [item.message.message_id for item in sorted_items]
            priority = max(
                sorted_items,
                key=lambda entry: PRIORITY_SCORE[entry.analysis.priority],
            ).analysis.priority
            tags = sorted({tag for item in sorted_items for tag in item.analysis.topic_tags})
            cluster_id = hashlib.sha1("|".join([group_name, category, entity_key] + source_ids).encode("utf-8")).hexdigest()
            representative_messages = [
                {
                    "message_id": item.message.message_id,
                    "sender_name": item.message.sender_name,
                    "content": item.message.normalized_content,
                    "priority": item.analysis.priority,
                }
                for item in sorted_items[:3]
            ]
            cluster = MessageCluster(
                cluster_id=cluster_id,
                group_name=group_name,
                category=category,
                priority=priority,
                source_message_ids=source_ids,
                representative_messages=representative_messages,
                tags=tags,
            )
            cluster.summary_hint = build_cluster_summary_hint(cluster)
            clusters.append(cluster)
        return clusters

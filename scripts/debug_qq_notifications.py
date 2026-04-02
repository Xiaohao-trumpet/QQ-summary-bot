from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.collector.qq_notification_collector import QQNotificationCollector
from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    collector = QQNotificationCollector(
        allowed_groups=settings.qq_allowed_group_list,
        group_filter_mode=settings.qq_group_filter_mode,
        app_names=settings.qq_notification_app_name_list,
        capture_private_chats=settings.qq_capture_private_chats,
    )

    print("QQ notification debug started")
    print(f"allowed_groups={settings.qq_allowed_group_list or 'ALL'}")
    print(f"filter_mode={settings.qq_group_filter_mode}")
    print(f"app_names={settings.qq_notification_app_name_list}")
    print("Waiting for QQ notifications. Press Ctrl+C to stop.")

    try:
        while True:
            messages = await collector.poll()
            for message in messages:
                print("-" * 60)
                print(f"group_name={message.group_name}")
                print(f"sender_name={message.sender_name}")
                print(f"timestamp={message.timestamp.isoformat()}")
                print(f"content={message.content}")
            await asyncio.sleep(1)
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())

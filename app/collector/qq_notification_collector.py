from __future__ import annotations

import ast
import asyncio
import hashlib
import logging
import re
import shutil
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from app.collector.base import BaseCollector
from app.schemas import RawQQMessage


LOGGER = logging.getLogger(__name__)

START_RE = re.compile(r"^(method call|signal).*\bmember=Notify\b")
UNREAD_SUFFIX_RE = re.compile(r"\s*[\(\（]\d+\s*(条新消息|unread)?[\)\）]\s*$", re.IGNORECASE)
SENDER_BODY_RE = re.compile(r"^(?P<sender>[^:：]{1,40})[:：]\s*(?P<content>.+)$")
GROUP_IN_SUMMARY_RE = [
    re.compile(r"^(?P<group>.+?群)\s*[\(\（](?P<sender>.+?)[\)\）]$"),
    re.compile(r"^(?P<group>.+?)\s*[-|｜]\s*(?P<sender>.+)$"),
    re.compile(r"^(?P<sender>.+?)\s*@\s*(?P<group>.+)$"),
]


@dataclass(slots=True)
class QQNotificationEvent:
    app_name: str
    summary: str
    body: str
    received_at: datetime


@dataclass(slots=True)
class ParsedQQNotification:
    group_name: str
    sender_name: str
    content: str


class QQNotificationCollector(BaseCollector):
    def __init__(
        self,
        allowed_groups: list[str] | None = None,
        group_filter_mode: str = "exact",
        app_names: list[str] | None = None,
        monitor_command: list[str] | None = None,
        capture_private_chats: bool = False,
    ) -> None:
        self.allowed_groups = [item.strip() for item in (allowed_groups or []) if item.strip()]
        self.group_filter_mode = group_filter_mode
        self.app_names = [item.strip() for item in (app_names or ["QQ", "linuxqq", "com.tencent.qq"]) if item.strip()]
        self.monitor_command = monitor_command or [
            "dbus-monitor",
            "--session",
            "interface='org.freedesktop.Notifications',member='Notify'",
        ]
        self.capture_private_chats = capture_private_chats

        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._queue: deque[RawQQMessage] = deque()

    async def poll(self) -> list[RawQQMessage]:
        await self._ensure_started()
        messages: list[RawQQMessage] = []
        while self._queue:
            messages.append(self._queue.popleft())
        return messages

    async def close(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self._process is not None:
            if self._process.returncode is None:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=3)
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
            self._process = None

    async def _ensure_started(self) -> None:
        if self._process is not None and self._process.returncode is None:
            return
        if shutil.which(self.monitor_command[0]) is None:
            raise RuntimeError(
                f"{self.monitor_command[0]} is not installed; cannot start QQ notification collector"
            )
        self._process = await asyncio.create_subprocess_exec(
            *self.monitor_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_notifications())
        LOGGER.info("started QQ notification collector using %s", self.monitor_command[0])

    async def _read_notifications(self) -> None:
        assert self._process is not None
        assert self._process.stdout is not None
        current_block: list[str] = []
        while True:
            line_bytes = await self._process.stdout.readline()
            if not line_bytes:
                if current_block:
                    self._handle_block(current_block)
                break
            line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")
            if START_RE.match(line):
                if current_block:
                    self._handle_block(current_block)
                current_block = [line]
                continue
            if not current_block:
                continue
            if not line.strip():
                self._handle_block(current_block)
                current_block = []
                continue
            current_block.append(line)

    def _handle_block(self, block: list[str]) -> None:
        event = self._parse_dbus_block(block)
        if event is None:
            return
        parsed = self._parse_notification_payload(event.summary, event.body)
        if parsed is None:
            return
        if not self._group_allowed(parsed.group_name):
            return
        message = self._build_message(parsed, event.received_at)
        self._queue.append(message)

    def _parse_dbus_block(self, block: list[str]) -> QQNotificationEvent | None:
        if not block or not START_RE.match(block[0]):
            return None

        strings: list[str] = []
        for line in block[1:]:
            stripped = line.strip()
            if stripped.startswith("string "):
                value = self._parse_dbus_string(stripped)
                if value is not None:
                    strings.append(value)
            if len(strings) >= 4:
                break
        if len(strings) < 4:
            return None

        app_name, _app_icon, summary, body = strings[:4]
        if self.app_names and app_name not in self.app_names:
            return None
        return QQNotificationEvent(
            app_name=app_name,
            summary=summary.strip(),
            body=body.strip(),
            received_at=datetime.now().astimezone(),
        )

    def _parse_notification_payload(self, summary: str, body: str) -> ParsedQQNotification | None:
        summary = self._normalize_group_name(summary)
        body = body.strip()
        if not summary or not body:
            return None

        match = SENDER_BODY_RE.match(body)
        if match:
            return ParsedQQNotification(
                group_name=summary,
                sender_name=match.group("sender").strip(),
                content=match.group("content").strip(),
            )

        for pattern in GROUP_IN_SUMMARY_RE:
            match = pattern.match(summary)
            if match:
                return ParsedQQNotification(
                    group_name=self._normalize_group_name(match.group("group")),
                    sender_name=match.group("sender").strip(),
                    content=body,
                )

        if self.allowed_groups:
            for group_name in self.allowed_groups:
                for prefix in (f"{group_name}:", f"{group_name}：", f"[{group_name}]"):
                    if body.startswith(prefix):
                        content = body[len(prefix) :].strip(" ]")
                        return ParsedQQNotification(
                            group_name=self._normalize_group_name(group_name),
                            sender_name=summary,
                            content=content,
                        )

        if self.capture_private_chats:
            return ParsedQQNotification(
                group_name=summary,
                sender_name=summary,
                content=body,
            )
        return None

    def _group_allowed(self, group_name: str) -> bool:
        if not self.allowed_groups:
            return True
        normalized = self._normalize_group_name(group_name)
        if self.group_filter_mode == "contains":
            return any(item in normalized or normalized in item for item in self.allowed_groups)
        return normalized in {self._normalize_group_name(item) for item in self.allowed_groups}

    def _build_message(self, parsed: ParsedQQNotification, received_at: datetime) -> RawQQMessage:
        content_hash = hashlib.sha1(
            f"{parsed.group_name}|{parsed.sender_name}|{parsed.content}|{received_at.isoformat()}".encode("utf-8")
        ).hexdigest()
        group_id = str(uuid.uuid5(uuid.NAMESPACE_URL, parsed.group_name))
        sender_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{parsed.group_name}:{parsed.sender_name}"))
        return RawQQMessage(
            message_id=content_hash,
            group_id=group_id,
            group_name=parsed.group_name,
            sender_id=sender_id,
            sender_name=parsed.sender_name or "未知发送人",
            timestamp=received_at,
            content=parsed.content,
            mentioned_me=False,
            message_type="text",
        )

    @staticmethod
    def _parse_dbus_string(value: str) -> str | None:
        try:
            return ast.literal_eval(value[len("string ") :])
        except (SyntaxError, ValueError):
            LOGGER.debug("failed to parse dbus string line: %s", value)
            return None

    @staticmethod
    def _normalize_group_name(group_name: str) -> str:
        normalized = group_name.strip()
        normalized = UNREAD_SUFFIX_RE.sub("", normalized)
        return normalized.strip()

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        payload[key.strip()] = value.strip().strip('"').strip("'")
    return payload


def _resolve_path(value: str | Path, default: Path) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        path = Path(value)
    if not path.is_absolute():
        return (PROJECT_ROOT / path).resolve()
    return path


class Settings(BaseModel):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./summary_bot.db"
    enable_scheduler: bool = False
    timezone: str = "Asia/Shanghai"

    message_source: str = "file"
    message_source_path: Path = PROJECT_ROOT / "data" / "mock_messages.jsonl"
    poll_interval_seconds: int = 60
    hourly_summary_interval_seconds: int = 3600
    qq_allowed_groups: str = ""
    qq_group_filter_mode: str = "exact"
    qq_notification_app_names: str = "QQ,linuxqq,com.tencent.qq,com.tencent.mobileqq"
    qq_capture_private_chats: bool = False
    collector_shared_token: str = ""
    mobile_title: str = "Summary Bot"

    alert_channels: str = "console"
    keyword_rules_path: Path = PROJECT_ROOT / "data" / "keyword_rules.json"

    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    openai_timeout: float = 60.0
    openai_max_retries: int = 3
    openai_temperature: float = 0.1

    classifier_llm_rule_threshold: float = 2.5
    classifier_critical_rule_threshold: float = 8.5
    classifier_high_rule_threshold: float = 6.0

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_base_url and self.openai_api_key and self.openai_model)

    @property
    def alert_channel_list(self) -> list[str]:
        return [item.strip() for item in self.alert_channels.split(",") if item.strip()]

    @property
    def qq_allowed_group_list(self) -> list[str]:
        return [item.strip() for item in self.qq_allowed_groups.split(",") if item.strip()]

    @property
    def qq_notification_app_name_list(self) -> list[str]:
        return [item.strip() for item in self.qq_notification_app_names.split(",") if item.strip()]


def _build_settings_payload() -> dict[str, Any]:
    dotenv_values = _load_dotenv(PROJECT_ROOT / ".env")
    merged = {**dotenv_values, **os.environ}
    payload: dict[str, Any] = {
        "app_env": merged.get("APP_ENV", "development"),
        "log_level": merged.get("LOG_LEVEL", "INFO"),
        "database_url": merged.get("DATABASE_URL", "sqlite:///./summary_bot.db"),
        "enable_scheduler": _parse_bool(merged.get("ENABLE_SCHEDULER"), False),
        "timezone": merged.get("TIMEZONE", "Asia/Shanghai"),
        "message_source": merged.get("MESSAGE_SOURCE", "file"),
        "message_source_path": _resolve_path(
            merged.get("MESSAGE_SOURCE_PATH", "data/mock_messages.jsonl"),
            PROJECT_ROOT / "data" / "mock_messages.jsonl",
        ),
        "poll_interval_seconds": int(merged.get("POLL_INTERVAL_SECONDS", "60")),
        "hourly_summary_interval_seconds": int(
            merged.get("HOURLY_SUMMARY_INTERVAL_SECONDS", "3600")
        ),
        "qq_allowed_groups": merged.get("QQ_ALLOWED_GROUPS", ""),
        "qq_group_filter_mode": merged.get("QQ_GROUP_FILTER_MODE", "exact"),
        "qq_notification_app_names": merged.get(
            "QQ_NOTIFICATION_APP_NAMES",
            "QQ,linuxqq,com.tencent.qq,com.tencent.mobileqq",
        ),
        "qq_capture_private_chats": _parse_bool(
            merged.get("QQ_CAPTURE_PRIVATE_CHATS"),
            False,
        ),
        "collector_shared_token": merged.get("COLLECTOR_SHARED_TOKEN", ""),
        "mobile_title": merged.get("MOBILE_TITLE", "Summary Bot"),
        "alert_channels": merged.get("ALERT_CHANNELS", "console"),
        "keyword_rules_path": _resolve_path(
            merged.get("KEYWORD_RULES_PATH", "data/keyword_rules.json"),
            PROJECT_ROOT / "data" / "keyword_rules.json",
        ),
        "openai_base_url": merged.get("OPENAI_BASE_URL", ""),
        "openai_api_key": merged.get("OPENAI_API_KEY", ""),
        "openai_model": merged.get("OPENAI_MODEL", ""),
        "openai_timeout": float(merged.get("OPENAI_TIMEOUT", "60")),
        "openai_max_retries": int(merged.get("OPENAI_MAX_RETRIES", "3")),
        "openai_temperature": float(merged.get("OPENAI_TEMPERATURE", "0.1")),
        "classifier_llm_rule_threshold": float(
            merged.get("CLASSIFIER_LLM_RULE_THRESHOLD", "2.5")
        ),
        "classifier_critical_rule_threshold": float(
            merged.get("CLASSIFIER_CRITICAL_RULE_THRESHOLD", "8.5")
        ),
        "classifier_high_rule_threshold": float(
            merged.get("CLASSIFIER_HIGH_RULE_THRESHOLD", "6.0")
        ),
    }
    return payload


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(**_build_settings_payload())

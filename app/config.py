from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(default="sqlite:///./summary_bot.db", alias="DATABASE_URL")
    enable_scheduler: bool = Field(default=False, alias="ENABLE_SCHEDULER")
    timezone: str = Field(default="Asia/Shanghai", alias="TIMEZONE")

    message_source: str = Field(default="file", alias="MESSAGE_SOURCE")
    message_source_path: Path = Field(
        default=PROJECT_ROOT / "data" / "mock_messages.jsonl",
        alias="MESSAGE_SOURCE_PATH",
    )
    poll_interval_seconds: int = Field(default=60, alias="POLL_INTERVAL_SECONDS")
    hourly_summary_interval_seconds: int = Field(
        default=3600,
        alias="HOURLY_SUMMARY_INTERVAL_SECONDS",
    )

    alert_channels: str = Field(default="console", alias="ALERT_CHANNELS")
    keyword_rules_path: Path = Field(
        default=PROJECT_ROOT / "data" / "keyword_rules.json",
        alias="KEYWORD_RULES_PATH",
    )

    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="", alias="OPENAI_MODEL")
    openai_timeout: float = Field(default=60.0, alias="OPENAI_TIMEOUT")
    openai_max_retries: int = Field(default=3, alias="OPENAI_MAX_RETRIES")
    openai_temperature: float = Field(default=0.1, alias="OPENAI_TEMPERATURE")

    classifier_llm_rule_threshold: float = Field(
        default=2.5,
        alias="CLASSIFIER_LLM_RULE_THRESHOLD",
    )
    classifier_critical_rule_threshold: float = Field(
        default=8.5,
        alias="CLASSIFIER_CRITICAL_RULE_THRESHOLD",
    )
    classifier_high_rule_threshold: float = Field(
        default=6.0,
        alias="CLASSIFIER_HIGH_RULE_THRESHOLD",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_base_url and self.openai_api_key and self.openai_model)

    @property
    def alert_channel_list(self) -> list[str]:
        return [item.strip() for item in self.alert_channels.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


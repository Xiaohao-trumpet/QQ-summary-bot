from __future__ import annotations

import json
import logging
from json import JSONDecodeError
from typing import Any

import httpx


LOGGER = logging.getLogger(__name__)


class SchemaValidationError(RuntimeError):
    pass


class OpenAICompatClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    async def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        payload = self._build_payload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        response_json = await self._request_chat(payload)
        return self._extract_content(response_json)

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self._chat_json_once(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    temperature=temperature,
                )
            except (httpx.HTTPError, JSONDecodeError, SchemaValidationError, ValueError) as exc:
                last_error = exc
                LOGGER.warning("chat_json attempt %s failed: %s", attempt + 1, exc)
        raise RuntimeError(f"chat_json failed after retries: {last_error}") from last_error

    async def _chat_json_once(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None,
        temperature: float,
    ) -> dict[str, Any]:
        payload = self._build_payload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        if schema is not None:
            payload["response_format"] = {"type": "json_object"}

        try:
            response_json = await self._request_chat(payload)
            content = self._extract_content(response_json)
        except httpx.HTTPStatusError as exc:
            if schema is None or exc.response.status_code != 400:
                raise
            LOGGER.info("response_format unsupported, falling back to text extraction")
            payload.pop("response_format", None)
            response_json = await self._request_chat(payload)
            content = self._extract_content(response_json)

        parsed = self._extract_json_object(content)
        if schema is not None and not self._basic_schema_validate(parsed, schema):
            raise SchemaValidationError("response does not satisfy schema")
        return parsed

    def _build_payload(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

    async def _request_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        LOGGER.debug("llm request model=%s payload_keys=%s", self.model, sorted(payload))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        LOGGER.debug("llm response keys=%s", sorted(data))
        return data

    @staticmethod
    def _extract_content(response_json: dict[str, Any]) -> str:
        choices = response_json.get("choices") or []
        if not choices:
            raise ValueError("missing choices in response")
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(str(item.get("text", "")))
            return "\n".join(texts)
        raise ValueError("unsupported content type")

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except JSONDecodeError:
            decoder = json.JSONDecoder()
            for index, char in enumerate(text):
                if char != "{":
                    continue
                try:
                    parsed, _ = decoder.raw_decode(text[index:])
                    if isinstance(parsed, dict):
                        return parsed
                except JSONDecodeError:
                    continue
            raise

    @staticmethod
    def _basic_schema_validate(payload: dict[str, Any], schema: dict[str, Any]) -> bool:
        if schema.get("type") == "object" and not isinstance(payload, dict):
            return False
        required = schema.get("required", [])
        return all(key in payload for key in required)


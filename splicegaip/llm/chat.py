"""Provider-agnostic chat client with native tool calling.

This is the transport used by the analysis copilot (``splicegaip.agent.copilot``).
It is deliberately independent of AutoGen: the copilot needs a *loop* over
``tools``/``tool_calls`` that is easy to bound, trace and unit-test, and it
must work with any OpenAI-compatible endpoint (DeepSeek, OpenAI, Moonshot,
vLLM, Ollama's OpenAI bridge...).

Design rules
------------
* **No silent degradation** — ``available`` is False without credentials and
  callers must choose an explicit offline path.
* **Bounded** — every call has a timeout, a retry budget and token accounting.
* **Vendor-safe** — DeepSeek's thinking mode breaks tool calling when
  ``reasoning_content`` is not echoed; this client forces thinking off for
  any request that carries tools (see :mod:`splicegaip.llm.client`).
* **Injectable** — tests pass a fake client with the same
  ``chat.completions.create`` surface.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from splicegaip.config import Settings
from splicegaip.llm.client import (
    detect_provider,
    effective_temperature,
    provider_extra_body,
)

#: Request-level defaults chosen for analysis chat (not bulk enrichment).
DEFAULT_TIMEOUT = 180.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_TOKENS = 4096


class ChatError(RuntimeError):
    """A model call failed in a way the caller must handle."""


@dataclass
class ChatUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0

    def add(self, usage: Mapping[str, Any] | None) -> None:
        if not usage:
            self.calls += 1
            return
        self.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        self.completion_tokens += int(usage.get("completion_tokens") or 0)
        self.total_tokens += int(usage.get("total_tokens") or 0)
        self.calls += 1

    def as_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "calls": self.calls,
        }


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str

    def as_message(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": self.arguments},
        }

    def parsed(self) -> dict[str, Any]:
        try:
            value = json.loads(self.arguments or "{}")
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}


@dataclass
class ChatResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    message: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, int] = field(default_factory=dict)
    latency_seconds: float = 0.0
    model: str = ""
    finish_reason: str = ""
    reasoning: str = ""

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


def _tool_call_dicts(raw_calls: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for index, call in enumerate(raw_calls or []):
        function = getattr(call, "function", None)
        if function is None and isinstance(call, Mapping):
            function = call.get("function") or {}
        name = getattr(function, "name", None) or (
            function.get("name") if isinstance(function, Mapping) else ""
        )
        arguments = getattr(function, "arguments", None) or (
            function.get("arguments") if isinstance(function, Mapping) else ""
        )
        call_id = getattr(call, "id", None) or (call.get("id") if isinstance(call, Mapping) else "")
        calls.append(ToolCall(
            id=str(call_id or f"call_{index}"),
            name=str(name or ""),
            arguments=str(arguments or "{}"),
        ))
    return calls


class ChatClient:
    """Thin wrapper around an OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.model = model or settings.llm.model or ""
        self.timeout = float(timeout)
        self.max_retries = max(int(max_retries), 0)
        self.max_tokens = int(max_tokens)
        self.sleep = sleep
        self.usage = ChatUsage()
        self.calls: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._client = client

    # ------------------------------------------------------------------
    @property
    def configured(self) -> bool:
        return bool(self.settings.llm.configured and self.model)

    @property
    def available(self) -> bool:
        if not self.configured:
            return False
        if self._client is not None:
            return True
        try:
            import openai  # noqa: F401
        except Exception:  # noqa: BLE001 - optional dependency
            return False
        return True

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except Exception as error:  # noqa: BLE001
            raise ChatError(f"openai package is not installed: {error}") from error
        self._client = OpenAI(
            api_key=self.settings.llm.api_key,
            base_url=self.settings.llm.base_url,
            timeout=self.timeout,
            max_retries=0,  # retries are handled here, with our own logging
        )
        return self._client

    # ------------------------------------------------------------------
    def _request_body(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] | None,
        *,
        temperature: float | None,
        response_format: Mapping[str, Any] | None,
        max_tokens: int | None,
        thinking: str | None = None,
    ) -> dict[str, Any]:
        has_tools = bool(tools)
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
        }
        if has_tools:
            body["tools"] = list(tools)
            body["tool_choice"] = "auto"
        extra = provider_extra_body(self.settings, tools_expected=has_tools)
        provider = detect_provider(self.settings)
        forced_thinking_off = (
            has_tools
            and provider == "deepseek"
            and extra.get("thinking", {}).get("type") == "enabled"
        )
        if thinking == "disabled" and provider == "deepseek":
            # Structured JSON extraction (planner/critic) does not need chain of
            # thought, and on DeepSeek the reasoning tokens can consume the whole
            # completion budget, yielding an empty `content`.
            extra = {"thinking": {"type": "disabled"}}
            forced_thinking_off = True
        if forced_thinking_off:
            # A forced thinking mode plus tools is a documented 400 on DeepSeek.
            extra = {"thinking": {"type": "disabled"}}
        effective = effective_temperature(self.settings, tools_expected=has_tools)
        if forced_thinking_off:
            # Thinking is off for this request, so sampling is legal again.
            effective = float(self.settings.llm.temperature or 0.0)
        chosen = temperature if temperature is not None else effective
        if chosen is not None:
            body["temperature"] = float(chosen)
        if max_tokens or self.max_tokens:
            body["max_tokens"] = int(max_tokens or self.max_tokens)
        if response_format:
            body["response_format"] = dict(response_format)
        if extra:
            body["extra_body"] = extra
        return body

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        name = type(error).__name__.lower()
        if any(marker in name for marker in ("ratelimit", "timeout", "connection", "internalserver", "apistatus")):
            return True
        status = getattr(error, "status_code", None)
        return isinstance(status, int) and (status >= 500 or status == 429)

    def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        response_format: Mapping[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        thinking: str | None = None,
    ) -> ChatResult:
        """Run one chat completion, retrying transient failures."""
        if not self.configured:
            raise ChatError("no LLM endpoint configured (MODEL_API_BASE_URL / MODEL_API_KEY / MODEL_NAME)")
        body = self._request_body(
            messages, tools, temperature=temperature,
            response_format=response_format, max_tokens=max_tokens,
            thinking=thinking,
        )
        client = self._ensure_client()
        last_error: Exception | None = None
        started = time.monotonic()
        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(**body)
                latency = time.monotonic() - started
                result = self._parse(response, latency)
                self.usage.add(result.usage)
                self.calls.append({
                    "model": result.model or self.model,
                    "latency_seconds": round(latency, 3),
                    "finish_reason": result.finish_reason,
                    "tool_calls": [call.name for call in result.tool_calls],
                    "usage": result.usage,
                    "attempt": attempt + 1,
                })
                return result
            except Exception as error:  # noqa: BLE001 - normalised below
                last_error = error
                self.errors.append(f"{type(error).__name__}: {str(error)[:300]}")
                if attempt >= self.max_retries or not self._is_retryable(error):
                    break
                self.sleep(min(2 ** attempt, 8))
        raise ChatError(f"chat completion failed: {type(last_error).__name__}: {str(last_error)[:400]}") from last_error

    def _parse(self, response: Any, latency: float) -> ChatResult:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ChatError("endpoint returned no choices")
        choice = choices[0]
        message = getattr(choice, "message", None)
        if message is None and isinstance(choice, Mapping):
            message = choice.get("message") or {}
        content = getattr(message, "content", None)
        if content is None and isinstance(message, Mapping):
            content = message.get("content")
        raw_calls = getattr(message, "tool_calls", None)
        if raw_calls is None and isinstance(message, Mapping):
            raw_calls = message.get("tool_calls")
        reasoning = ""
        extra = getattr(message, "model_extra", None) or {}
        if isinstance(extra, Mapping):
            reasoning = str(extra.get("reasoning_content") or "")
        usage = getattr(response, "usage", None)
        usage_dict = {}
        if usage is not None:
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        tool_calls = _tool_call_dicts(raw_calls)
        assistant_message: dict[str, Any] = {"role": "assistant", "content": content or ""}
        if tool_calls:
            assistant_message["tool_calls"] = [call.as_message() for call in tool_calls]
        return ChatResult(
            text=str(content or ""),
            tool_calls=tool_calls,
            message=assistant_message,
            usage=usage_dict,
            latency_seconds=round(latency, 3),
            model=str(getattr(response, "model", "") or self.model),
            finish_reason=str(getattr(choice, "finish_reason", "") or ""),
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "available": self.available,
            "provider": detect_provider(self.settings),
            "model": self.model,
            "base_url": self.settings.llm.base_url,
            "usage": self.usage.as_dict(),
            "errors": self.errors[-3:],
        }

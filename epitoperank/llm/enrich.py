"""Optional LLM enrichment engine.

Everything here is *advisory*: when a model endpoint is configured the
platform asks it to enrich deterministic output (goal understanding,
planning, narrative interpretation, per-gene annotation, literature
summaries, limitations, hypotheses, critique); when the endpoint is
missing, slow or wrong, the deterministic result is returned unchanged.

Design rules that keep this safe:

* :class:`LLMEnhancer` never raises — every failure is recorded in
  ``errors`` and the caller keeps its deterministic value;
* a per-run call budget prevents runaway cost;
* responses are cached by (model, prompt) so repeated renders are free;
* JSON is parsed tolerantly (raw, fenced, or embedded in prose);
* the engine works from sync *and* async contexts (it never calls
  ``asyncio.run`` inside a running loop).

Credentials are read from the environment only (see
:mod:`epitoperank.config`); nothing here writes secrets anywhere.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Mapping, Sequence

from epitoperank.config import Settings
from epitoperank.llm.client import (
    build_model_client,
    detect_provider,
    effective_temperature,
    resolve_reasoning_effort,
    resolve_thinking,
)

#: Features that may call the model. ``EPITOPERANK_LLM_FEATURES`` or the
#: ``llm.features`` config block selects a subset; "all" enables everything.
ALL_FEATURES: tuple[str, ...] = (
    "understand",  # query / intent understanding
    "plan",  # planner goal + limitation refinement
    "interpret",  # narrative interpretation of the results
    "annotate",  # per-gene biological annotation
    "literature",  # literature evidence summarisation
    "limitations",  # additional study-design limitations
    "hypotheses",  # hypotheses + validation suggestions
    "critique",  # self-critique of the narrative
    "ingest",  # messy input profiling + field mapping
)

_JSON_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)
_CJK = re.compile(r"[\u4e00-\u9fff]")


# 中文备注：大模型层：执行异步（参数：coro）
def run_async(coro: Any) -> Any:
    """Run a coroutine from sync code, also when a loop is already running.

    The enrichment layer is called from three places: the pipeline
    (sync), the FastAPI handlers (sync) and the agent tools (inside the
    team's event loop). ``asyncio.run`` raises in the last case, so the
    coroutine is executed in a worker thread with its own loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


# 中文备注：大模型层：提取JSON（参数：text）
def extract_json(text: str | None) -> Any:
    """Parse JSON from a model reply (raw, fenced, or embedded in prose)."""
    raw = (text or "").strip()
    if not raw:
        return None
    for candidate in (raw, *_fenced(raw), *_braced(raw)):
        try:
            return json.loads(candidate)
        except (ValueError, TypeError):
            continue
    return None


def _fenced(raw: str) -> list[str]:
    """提取回复中围栏代码块（```json 等）里的内容，供宽松 JSON 解析使用。"""
    return [match.group(1).strip() for match in _JSON_FENCE.finditer(raw)]


def _braced(raw: str) -> list[str]:
    """截取首个 { 或 [ 到最后一个 } 或 ] 之间的片段，用于从散文里捞 JSON。"""
    candidates: list[str] = []
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        end = raw.rfind(closer)
        if start >= 0 and end > start:
            candidates.append(raw[start : end + 1])
    return candidates


# 中文备注：大模型层：检测语言（参数：query、configured）
def detect_language(query: str, configured: str = "auto") -> str:
    """Pick the language for generated prose ("zh" or "en")."""
    setting = (configured or "auto").strip().lower()
    if setting in {"zh", "zh-cn", "chinese", "中文"}:
        return "zh"
    if setting in {"en", "en-us", "english"}:
        return "en"
    return "zh" if _CJK.search(query or "") else "en"


class LLMEnhancer:
    """Thin, failure-tolerant wrapper around the configured model client."""

    def __init__(
        self,
        settings: Settings,
        *,
        logger: Callable[[str, str, str, str], None] | None = None,
        features: Iterable[str] | None = None,
        recorder: Any | None = None,
    ) -> None:
        """按配置初始化功能开关、调用预算、超时、缓存与重试参数，不做任何网络请求。"""
        self.recorder = recorder
        self.settings = settings
        self.logger = logger
        llm = settings.llm
        if features is not None:
            self.features = {item for item in features if item in ALL_FEATURES}
        elif llm.features:
            lowered = {str(item).strip().lower() for item in llm.features}
            if "all" in lowered:
                self.features = set(ALL_FEATURES)
            else:
                self.features = {item for item in lowered if item in ALL_FEATURES}
        else:
            self.features = set(ALL_FEATURES)
        self.max_calls = max(int(llm.max_calls_per_run or 0), 0)
        self.timeout = float(llm.insight_timeout_seconds or 120.0)
        self.temperature = float(llm.temperature or 0.2)
        self.max_genes = max(int(llm.max_genes or 8), 1)
        self._cache: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []
        self.errors: list[dict[str, str]] = []
        # Transient-failure retries: a single empty body / timeout / connection
        # reset from the endpoint must not silently downgrade every feature to
        # its deterministic fallback (that looks exactly like "the key is not
        # used"). Tunable without touching the settings schema.
        self.max_retries = max(int(os.getenv("EPITOPERANK_LLM_RETRIES", "3") or 3), 1)
        self.retry_backoff = max(float(os.getenv("EPITOPERANK_LLM_RETRY_BACKOFF", "1.5") or 1.5), 0.0)

    # -- state ------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        """凭据可用且至少启用了一个功能时才为真。"""
        from .trace import ACTIVE
        trace = self.recorder or ACTIVE.get()
        usable = trace.meta.get("llm_enabled", False) if trace and trace.replay else self.settings.llm.usable
        return bool(usable) and bool(self.features)

    @property
    def model(self) -> str:
        """返回配置的主模型名，未配置时为空串。"""
        return self.settings.llm.model or ""

    @property
    def critic_model(self) -> str:
        """返回自评使用的模型，未单独配置时回退到主模型。"""
        return self.settings.llm.critic_model or self.model

    def has(self, feature: str) -> bool:
        """判断某个功能是否启用（整体可用且该功能在启用集合内）。"""
        return self.enabled and feature in self.features

    def _budget_left(self) -> bool:
        """判断本次运行是否还有调用额度；预算为 0 表示不限。"""
        return not self.max_calls or len(self.calls) < self.max_calls

    def _note(self, status: str, feature: str, detail: str) -> None:
        """把一次调用的状态写入日志回调，日志自身异常会被吞掉以免影响主流程。"""
        if self.logger is not None:
            try:
                self.logger("llm", f"enrich:{feature}", status, detail[:400])
            except Exception:  # noqa: BLE001 - logging must never break a run
                pass

    # -- completion -------------------------------------------------------
    # 中文备注：大模型层：调用once（参数：system、user、model、max_tokens）
    def _call_once(
        self,
        system: str,
        user: str,
        model: str | None,
        max_tokens: int | None,
        json_output: bool,
        timeout: float,
        feature: str,
    ) -> str | None:
        """A single model call (with the json-output format fallback).

        Returns the raw text, or ``None`` on any failure. Failures are recorded
        in :attr:`errors` so the caller can surface them to the UI.
        """
        self._trace_attempts = getattr(self, "_trace_attempts", 0) + 1
        try:
            return run_async(
                self._create(
                    system,
                    user,
                    model=model,
                    max_tokens=max_tokens,
                    json_output=json_output,
                    timeout=timeout,
                )
            )
        except Exception as error:  # noqa: BLE001 - every failure degrades
            self.errors.append({"feature": feature or "generic", "error": str(error)})
            self._note("error", feature or "generic", str(error))
            if json_output:
                # Some OpenAI-compatible gateways reject structured output;
                # retry once as plain text and parse it ourselves.
                try:
                    self._trace_attempts += 1
                    return run_async(
                        self._create(
                            system,
                            user,
                            model=model,
                            max_tokens=max_tokens,
                            json_output=False,
                            timeout=timeout,
                        )
                    )
                except Exception as retry_error:  # noqa: BLE001
                    self.errors.append(
                        {"feature": feature or "generic", "error": f"retry: {retry_error}"}
                    )
            return None

    # 中文备注：统一的模型调用录制/重放边界（参数：无）
    def request(self, **kwargs):
        """Injectable recording/replay boundary, outside complete (the network guard)."""
        from .trace import ACTIVE
        trace = getattr(self, "recorder", None) or ACTIVE.get()
        if trace is not None:
            return trace.request(self, kwargs)
        kwargs.pop("stage", None)
        return self.complete(**kwargs)

    # 中文备注：执行一次模型调用并返回文本（参数：system、user、feature、model）
    def complete(
        self,
        *,
        system: str,
        user: str,
        feature: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_output: bool = False,
        timeout: float | None = None,
    ) -> str | None:
        """One model call; ``None`` when unavailable, skipped or failed.

        Transient failures (empty body, timeout, connection reset) are retried
        a few times so a single endpoint hiccup does not silently downgrade
        every feature to its deterministic fallback — which would otherwise
        look exactly like "the API key is not being used".
        """
        from .trace import ACTIVE, ReplayError
        trace = self.recorder or ACTIVE.get()
        if trace is not None and trace.replay:
            raise ReplayError("LLMEnhancer.complete called during replay")
        if feature and not self.has(feature):
            return None
        if not self.enabled:
            return None
        if not self._budget_left():
            self._note("skip", feature or "generic", "call budget exhausted")
            return None
        eff_timeout = float(timeout or self.timeout)
        key = hashlib.sha1(
            "\n".join([str(model or ""), system, user, "json" if json_output else "text"]).encode("utf-8")
        ).hexdigest()
        if key in self._cache:
            return self._cache[key]

        text: str | None = None
        feature_name = feature or "generic"
        for attempt in range(self.max_retries):
            # Cap the per-attempt timeout on retries so a slow endpoint cannot
            # multiply the wait across every retry.
            attempt_timeout = eff_timeout if attempt == 0 else min(eff_timeout, 45.0)
            candidate = self._call_once(
                system, user, model, max_tokens, json_output, attempt_timeout, feature_name
            )
            if candidate and candidate.strip():
                text = candidate
                break
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_backoff)
        if not text or not text.strip():
            if not self.errors:
                self.errors.append(
                    {
                        "feature": feature_name,
                        "error": f"no usable response after {self.max_retries} attempts (endpoint busy/empty)",
                    }
                )
            return None
        self._cache[key] = text
        self.calls.append(
            {
                "feature": feature_name,
                "model": model or self.model,
                "chars": len(text),
            }
        )
        return text

    # 中文备注：请求模型返回 JSON 并解析为对象（参数：system、user、feature、model）
    def json(
        self,
        *,
        system: str,
        user: str,
        feature: str = "",
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Model call parsed as JSON; ``None`` on any failure."""
        text = self.request(
            system=system,
            user=user,
            feature=feature,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            json_output=True,
            timeout=timeout,
        )
        if text is None:
            return None
        parsed = extract_json(text)
        if parsed is not None:
            return parsed
        # Some providers return JSON wrapped in prose even with json_output on,
        # or emit a non-JSON acknowledgement. Retry once as plain text and try
        # to recover the JSON from reasoning/prose before giving up.
        self._note("retry", feature or "generic", "JSON parse failed; retrying as plain text")
        text = self.request(
            system=system,
            user=user,
            feature=feature,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            json_output=False,
            timeout=timeout,
        )
        if text is None:
            self.errors.append({"feature": feature or "generic", "error": "unparseable JSON"})
            self._note("error", feature or "generic", "unparseable JSON response")
            return None
        parsed = extract_json(text)
        if parsed is None:
            self.errors.append({"feature": feature or "generic", "error": "unparseable JSON"})
            self._note("error", feature or "generic", "unparseable JSON response after retry")
        return parsed

    # -- plumbing ---------------------------------------------------------
    async def _create(
        self,
        system: str,
        user: str,
        *,
        model: str | None,
        max_tokens: int | None,
        json_output: bool,
        timeout: float,
    ) -> str:
        """发起一次真实模型调用（联网、受 timeout 约束）；失败时异常上抛，由上层降级。"""
        from autogen_core.models import SystemMessage, UserMessage

        messages: list[Any] = [SystemMessage(content=system), UserMessage(content=user, source="user")]
        # The enrichment layer never sends tools, so thinking *could* be safe on
        # DeepSeek. But in practice DeepSeek's thinking burns the entire
        # ``max_tokens`` budget on ``reasoning_content`` and returns an empty
        # final ``content`` (finish_reason="length"), which silently looks like
        # "the key is not being used". Treat the enrichment layer like the agent
        # team — disable thinking — so the full token budget reaches the answer.
        client = build_model_client(self.settings, model=model, tools_expected=True)
        try:
            kwargs: dict[str, Any] = {}
            try:
                parameters = inspect.signature(client.create).parameters
                if "json_output" in parameters:
                    kwargs["json_output"] = bool(json_output)
                if "extra_create_args" in parameters:
                    extra: dict[str, Any] = {}
                    sampling = effective_temperature(self.settings, tools_expected=True)
                    if sampling is not None:
                        extra["temperature"] = float(sampling)
                    if max_tokens:
                        extra["max_tokens"] = int(max_tokens)
                    if extra:
                        kwargs["extra_create_args"] = extra
            except (TypeError, ValueError):  # pragma: no cover - defensive
                kwargs = {}
            result = await asyncio.wait_for(client.create(messages, **kwargs), timeout=timeout)
        finally:
            try:
                await client.close()
            except Exception:  # noqa: BLE001
                pass
        return _as_text(result)

    # -- reporting --------------------------------------------------------
    # 中文备注：大模型层：描述describe（参数：无）
    def describe(self) -> dict[str, Any]:
        """Status payload for the API and the UI."""
        llm = self.settings.llm
        provider = detect_provider(self.settings)
        try:
            effort = resolve_reasoning_effort(self.settings) or "vendor default"
        except Exception:  # noqa: BLE001 - status must never 500
            effort = "vendor default"
        return {
            "enabled": self.enabled,
            "configured": llm.configured,
            "model": self.model,
            "critic_model": self.critic_model,
            "base_url": _redact(llm.base_url),
            "provider": provider,
            "thinking_agent": resolve_thinking(self.settings, tools_expected=True) or "n/a",
            "thinking_insight": resolve_thinking(self.settings, tools_expected=True) or "n/a",
            "reasoning_effort": effort,
            "features": sorted(self.features),
            "available_features": list(ALL_FEATURES),
            "max_calls": self.max_calls,
            "max_genes": self.max_genes,
            "timeout_seconds": self.timeout,
            "calls": list(self.calls),
            "errors": list(self.errors),
            "call_count": len(self.calls),
        }


def _as_text(result: Any) -> str:
    """把模型返回的 content（字符串、内容块列表或对象）统一拼成纯文本。"""
    content = getattr(result, "content", result)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            text = getattr(item, "content", None)
            if text is None and isinstance(item, Mapping):
                text = item.get("content")  # type: ignore[union-attr]
            if text:
                parts.append(str(text))
        return "\n".join(parts)
    return str(content)


# 中文备注：大模型层：辅助处理redact（参数：url）
def _redact(url: str) -> str:
    """Show the endpoint host but never credentials or query strings."""
    value = (url or "").strip()
    if not value:
        return ""
    stripped = value.split("?")[0]
    if "@" in stripped:
        stripped = stripped.split("@", 1)[1]
    return stripped


# 中文备注：大模型层：构建enhancer（参数：settings、logger）
def build_enhancer(
    settings: Settings | None = None,
    *,
    logger: Callable[[str, str, str, str], None] | None = None,
) -> LLMEnhancer:
    """Build an enhancer for ``settings`` (loading defaults when omitted)."""
    if settings is None:
        from epitoperank.config import load_settings

        settings = load_settings()
    return LLMEnhancer(settings, logger=logger)


# 中文备注：大模型层：辅助处理大模型状态（参数：settings）
def llm_status(settings: Settings | None = None) -> dict[str, Any]:
    """Model status without making any call (used by the API/UI)."""
    try:
        enhancer = build_enhancer(settings)
    except Exception as error:  # noqa: BLE001 - status must never 500
        return {"enabled": False, "configured": False, "error": str(error)}
    return enhancer.describe()


def env_flag(name: str, default: bool = False) -> bool:
    """按常见真假值解析环境变量开关，变量未设置时返回默认值。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

"""Deterministic, scriptable chat client for tests and offline evaluation.

A real agent loop is hard to unit-test because the model decides the next move.
:class:`ScriptedChat` replaces the model with a list of steps, while keeping the
exact ``ChatClient`` surface (``complete``, ``usage``, ``status``), so the whole
copilot loop — planning, tool execution, critique, revision — can run in CI
without network access or API keys.

Each script step is one of::

    {"tools": [{"name": "project_overview", "arguments": {}}]}
    {"text": "## 结论\\n..."}
    {"error": "simulated failure"}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from epitoperank.llm.chat import ChatError, ChatResult, ChatUsage, ToolCall


@dataclass
class ScriptedChat:
    script: list[dict[str, Any]] = field(default_factory=list)
    model: str = "scripted"
    configured: bool = True
    available: bool = True
    usage: ChatUsage = field(default_factory=ChatUsage)
    calls: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    _index: int = 0

    def _next(self) -> dict[str, Any]:
        if not self.script:
            return {"text": ""}
        step = self.script[min(self._index, len(self.script) - 1)]
        self._index += 1
        return step if isinstance(step, dict) else {"text": str(step)}

    def complete(self, messages: Sequence[Mapping[str, Any]], *,
                 tools: Sequence[Mapping[str, Any]] | None = None,
                 response_format: Mapping[str, Any] | None = None,
                 temperature: float | None = None,
                 max_tokens: int | None = None,
                 thinking: str | None = None) -> ChatResult:
        step = self._next()
        if step.get("error"):
            self.errors.append(str(step["error"]))
            raise ChatError(str(step["error"]))
        raw_tools = step.get("tools") or []
        if raw_tools and tools:
            calls = [
                ToolCall(id=f"call_{self._index}_{index}", name=str(item.get("name")),
                         arguments=json.dumps(item.get("arguments") or {}, ensure_ascii=False))
                for index, item in enumerate(raw_tools)
                if isinstance(item, Mapping) and item.get("name")
            ]
            message: dict[str, Any] = {
                "role": "assistant",
                "content": str(step.get("text") or ""),
                "tool_calls": [call.as_message() for call in calls],
            }
            result = ChatResult(text=str(step.get("text") or ""), tool_calls=calls,
                                message=message, model=self.model)
        else:
            text = str(step.get("text") or "")
            result = ChatResult(
                text=text,
                message={"role": "assistant", "content": text},
                model=self.model,
                usage={"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180},
            )
        self.usage.add(result.usage)
        self.calls.append({
            "model": self.model,
            "tools_offered": len(tools or []),
            "tool_calls": [call.name for call in result.tool_calls],
            "has_response_format": bool(response_format),
        })
        return result

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "available": self.available,
            "provider": "scripted",
            "model": self.model,
            "base_url": "",
            "usage": self.usage.as_dict(),
            "errors": self.errors[-3:],
        }

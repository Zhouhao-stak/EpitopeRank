"""Deterministic (offline) model client.

Implements the AutoGen ``ChatCompletionClient`` interface with a
queue-replay policy: the deterministic analysis policy pre-computes the
full response script for each agent (plan text, tool calls with concrete
arguments, final summaries), and this client replays it through the real
AutoGen tool-calling machinery.

Consequences:

* the multi-agent team, tool execution and termination protocol are the
  same code paths as in LLM mode;
* the pipeline cannot loop forever (queues drain, then the client
  returns the final message containing the termination token);
* switching to a real LLM requires no code change — only credentials.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import AsyncGenerator, Sequence
from typing import Any, Callable

from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,
    ModelInfo,
    RequestUsage,
)

#: Token that terminates the team run (TextMentionTermination).
TERMINATION_TOKEN = "EPITOPERANK_DONE"

_ZERO_USAGE = RequestUsage(prompt_tokens=0, completion_tokens=0)


def _text_result(text: str) -> CreateResult:
    """构造一个纯文本的停止结果，供离线回放使用（不产生 token 用量）。"""
    return CreateResult(
        finish_reason="stop",
        content=text,
        usage=_ZERO_USAGE,
        cached=False,
    )


def _tool_result(call_id: str, name: str, arguments: dict[str, Any]) -> CreateResult:
    """构造一个函数调用结果，把脚本化的工具名与参数包装成 AutoGen 可消费的形状。"""
    return CreateResult(
        finish_reason="function_calls",
        content=[{"id": call_id, "name": name, "arguments": json.dumps(arguments)}],
        usage=_ZERO_USAGE,
        cached=False,
    )


class DeterministicClient(ChatCompletionClient):
    """Queue-replay model client for one agent."""

    def __init__(
        self,
        agent_name: str,
        script: Sequence[dict[str, Any]] | None = None,
        finalizer: Callable[[], str] | None = None,
    ) -> None:
        """初始化该 agent 的回放队列、收尾回调和调用计数，不建立任何网络连接。"""
        self._agent_name = agent_name
        self._queue: deque[dict[str, Any]] = deque(script or [])
        self._finalizer = finalizer
        self._call_count = 0

    # -- scripting --------------------------------------------------------
    # 中文备注：大模型层：辅助处理enqueue（参数：item）
    def enqueue(self, item: dict[str, Any]) -> None:
        """Append a scripted response (``{"text": ...}`` or ``{"tool": name, "args": {...}}``)."""
        self._queue.append(item)

    def set_finalizer(self, finalizer: Callable[[], str]) -> None:
        """设置队列耗尽后生成收尾文本的回调。"""
        self._finalizer = finalizer

    # -- ChatCompletionClient interface -----------------------------------
    @property
    def capabilities(self) -> ModelCapabilities:
        """声明不支持视觉、但支持函数调用与 JSON 输出。"""
        return ModelCapabilities(vision=False, function_calling=True, json_output=True)

    @property
    def model_info(self) -> ModelInfo:
        """返回固定为 deterministic 家族的模型元信息，供 AutoGen 校验。"""
        return ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="deterministic",
            structured_output=True,
            multiple_system_messages=True,
        )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> CreateResult:
        """按脚本顺序回放一次响应；队列为空时用 finalizer 或直接返回终止令牌，永不联网也不会死循环。"""
        self._call_count += 1
        if self._queue:
            item = self._queue.popleft()
            if "tool" in item:
                return _tool_result(
                    call_id=f"det-{self._agent_name}-{self._call_count}",
                    name=str(item["tool"]),
                    arguments=dict(item.get("args", {})),
                )
            return _text_result(str(item.get("text", "")))
        if self._finalizer is not None:
            return _text_result(self._finalizer())
        return _text_result(f"{self._agent_name} finished. {TERMINATION_TOKEN}")

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        **kwargs: Any,
    ) -> AsyncGenerator[str | CreateResult, None]:
        """把 create 的单次结果包装成异步流，仅为满足接口签名。"""
        yield await self.create(messages, tools=tools, **kwargs)

    async def close(self) -> None:
        """空实现：离线客户端没有需要释放的连接。"""
        return None

    def actual_usage(self) -> RequestUsage:
        """返回零用量：回放不消耗任何 token。"""
        return _ZERO_USAGE

    def total_usage(self) -> RequestUsage:
        """返回零用量：回放不消耗任何 token。"""
        return _ZERO_USAGE

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        """恒返回 0，离线回放无需估算 token。"""
        return 0

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        """返回固定的剩余额度，避免 AutoGen 误判上下文耗尽。"""
        return 100000


class DeterministicSelectorClient(ChatCompletionClient):
    """Selector model client that replays a planned speaker order."""

    def __init__(self, speaker_order: Sequence[str], participants: Sequence[str]) -> None:
        """保存预定的发言顺序与参与者名单。"""
        self._order = deque(speaker_order)
        self._participants = list(participants)

    def _next_speaker(self) -> str:
        """取出下一个仍在参与者名单中的预定发言人；顺序耗尽则回退到最后一位（解释器）。"""
        while self._order:
            candidate = self._order.popleft()
            if candidate in self._participants:
                return candidate
        # Fall back to the interpreter (it holds the termination token).
        return self._participants[-1]

    @property
    def capabilities(self) -> ModelCapabilities:
        """声明不支持视觉、但支持函数调用与 JSON 输出。"""
        return ModelCapabilities(vision=False, function_calling=True, json_output=True)

    @property
    def model_info(self) -> ModelInfo:
        """返回固定为 deterministic-selector 家族的模型元信息。"""
        return ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="deterministic-selector",
            structured_output=True,
            multiple_system_messages=True,
        )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> CreateResult:
        """返回一句指明下一位发言者的固定文本，驱动 SelectorGroupChat 选人，不联网。"""
        speaker = self._next_speaker()
        return _text_result(f"The next agent to perform the task is {speaker}.")

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        **kwargs: Any,
    ) -> AsyncGenerator[str | CreateResult, None]:
        """把 create 的单次结果包装成异步流，仅为满足接口签名。"""
        yield await self.create(messages, tools=tools, **kwargs)

    async def close(self) -> None:
        """空实现：离线选择器没有需要释放的连接。"""
        return None

    def actual_usage(self) -> RequestUsage:
        """返回零用量。"""
        return _ZERO_USAGE

    def total_usage(self) -> RequestUsage:
        """返回零用量。"""
        return _ZERO_USAGE

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        """恒返回 0。"""
        return 0

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        """返回固定的剩余额度。"""
        return 100000

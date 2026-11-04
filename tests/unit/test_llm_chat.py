"""Tests for the tool-calling chat transport."""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

import pytest

from splicegaip.config import LLMSettings, load_settings
from splicegaip.llm.chat import ChatClient, ChatError


def make_settings(**overrides):
    base = load_settings("tests/fixtures/config_test.yaml")
    llm = LLMSettings(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="fake-model",
        timeout_seconds=5,
        **overrides,
    )
    return dataclasses.replace(base, llm=llm)


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeOpenAI:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def response(text: str = "", tool_calls=None, usage=(11, 7, 18)):
    message = SimpleNamespace(content=text, tool_calls=tool_calls, model_extra={})
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=usage[0], completion_tokens=usage[1],
                              total_tokens=usage[2]),
        model="fake-model",
    )


def tool_call(call_id: str, name: str, arguments: dict):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(
        name=name, arguments=json.dumps(arguments)))


class APIConnectionError(Exception):
    """Name-based retry classification is intentional in chat.py."""


def test_text_completion_and_usage() -> None:
    fake = FakeOpenAI([response("hello")])
    client = ChatClient(make_settings(), client=fake, sleep=lambda _: None)
    result = client.complete([{"role": "user", "content": "hi"}])
    assert result.text == "hello"
    assert result.usage["total_tokens"] == 18
    assert client.usage.calls == 1
    assert fake.chat.completions.calls[0]["model"] == "fake-model"


def test_tool_calls_are_parsed() -> None:
    fake = FakeOpenAI([response(tool_calls=[tool_call("c1", "query_events",
                                                      {"gene": "TP53", "limit": 5})])])
    client = ChatClient(make_settings(), client=fake, sleep=lambda _: None)
    result = client.complete([{"role": "user", "content": "hi"}],
                             tools=[{"type": "function", "function": {"name": "query_events"}}])
    assert result.wants_tools
    assert result.tool_calls[0].name == "query_events"
    assert result.tool_calls[0].parsed() == {"gene": "TP53", "limit": 5}
    assert result.message["tool_calls"][0]["function"]["name"] == "query_events"


def test_transient_error_is_retried() -> None:
    fake = FakeOpenAI([APIConnectionError("boom"), response("recovered")])
    client = ChatClient(make_settings(), client=fake, max_retries=1, sleep=lambda _: None)
    result = client.complete([{"role": "user", "content": "hi"}])
    assert result.text == "recovered"
    assert client.usage.calls == 1


def test_non_retryable_error_raises() -> None:
    fake = FakeOpenAI([ValueError("bad request")])
    client = ChatClient(make_settings(), client=fake, max_retries=2, sleep=lambda _: None)
    with pytest.raises(ChatError):
        client.complete([{"role": "user", "content": "hi"}])
    assert len(fake.chat.completions.calls) == 1


def test_unconfigured_client_is_unavailable() -> None:
    base = load_settings("tests/fixtures/config_test.yaml")
    # Build the empty block explicitly: the developer's .env may be loaded by
    # another test module during collection, and the environment overrides YAML.
    settings = dataclasses.replace(base, llm=LLMSettings())
    client = ChatClient(settings)
    assert client.available is False
    with pytest.raises(ChatError):
        client.complete([{"role": "user", "content": "hi"}])


def test_tool_request_body_forces_thinking_off(monkeypatch) -> None:
    """DeepSeek + tools must not request thinking (documented 400 otherwise)."""
    settings = make_settings(provider="deepseek", thinking="enabled")
    fake = FakeOpenAI([response("ok")])
    client = ChatClient(settings, client=fake, sleep=lambda _: None)
    client.complete([{"role": "user", "content": "hi"}],
                    tools=[{"type": "function", "function": {"name": "x"}}])
    body = fake.chat.completions.calls[0]
    assert body["extra_body"]["thinking"]["type"] == "disabled"
    # Temperature is omitted for thinking requests; here thinking is off, so
    # the configured temperature is allowed through.
    assert "temperature" in body

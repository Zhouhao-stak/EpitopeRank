"""Tests for the tool-using analysis copilot."""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

import pytest

from epitoperank.agent.copilot import CopilotTools, ask, status
from epitoperank.config import LLMSettings, load_settings
from epitoperank.llm.chat import ChatClient
from epitoperank.memory.project_memory import ProjectMemory

PROJECT = "SPN-TEST0001"


def make_settings(tmp_path, *, configured: bool = False):
    base = load_settings("tests/fixtures/config_test.yaml")
    paths = dataclasses.replace(
        base.paths,
        runtime_root=tmp_path,
        memory_db=tmp_path / "memory.sqlite3",
        literature_db=tmp_path / "literature.sqlite3",
    )
    llm = LLMSettings(
        base_url="https://example.invalid/v1" if configured else "",
        api_key="test-key" if configured else "",
        model="fake-model" if configured else "",
    )
    return dataclasses.replace(base, paths=paths, llm=llm)


def seed_project(settings, tmp_path, *, source_dir=None):
    memory = ProjectMemory(settings.paths.memory_db)
    memory.create_project(PROJECT, "demo", "test query",
                          source_dir=str(source_dir or tmp_path))
    return memory


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeOpenAI:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def response(text: str = "", tool_calls=None):
    message = SimpleNamespace(content=text, tool_calls=tool_calls, model_extra={})
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=6, total_tokens=18),
        model="fake-model",
    )


def tool_call(call_id: str, name: str, arguments: dict):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(
        name=name, arguments=json.dumps(arguments)))


class TestTools:
    def test_overview_reads_project_memory(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        seed_project(settings, tmp_path)
        tools = CopilotTools(settings, project_id=PROJECT)
        result = tools.execute("project_overview", {})
        assert result.ok
        assert result.data["project_id"] == PROJECT
        assert result.data["events"] == 0

    def test_invalid_arguments_are_rejected_before_execution(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        seed_project(settings, tmp_path)
        tools = CopilotTools(settings, project_id=PROJECT)
        result = tools.execute("query_events", {"limit": 999})
        assert not result.ok
        assert "maximum" in result.error

    def test_unknown_project_is_reported(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        tools = CopilotTools(settings, project_id="SPN-MISSING")
        result = tools.execute("project_overview", {})
        assert not result.ok

    def test_unknown_tool_is_reported(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        tools = CopilotTools(settings, project_id=PROJECT)
        result = tools.execute("drop_database", {})
        assert not result.ok
        assert result.error == "unknown_tool"

    def test_specs_are_openai_function_schemas(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        tools = CopilotTools(settings)
        for spec in tools.specs():
            assert spec["type"] == "function"
            assert spec["function"]["name"]
            assert spec["function"]["parameters"]["type"] == "object"


class TestOffline:
    def test_offline_briefing_uses_project_facts(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        seed_project(settings, tmp_path)
        answer = ask("项目里有什么？", settings, project_id=PROJECT, force_offline=True)
        assert answer.mode == "offline"
        assert "结论" in answer.answer
        assert any(call["tool"] == "project_overview" for call in answer.tool_calls)
        assert answer.grounding["severity"] == "ok"

    def test_offline_without_project_lists_projects(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        think = ask("有哪些项目？", settings, force_offline=True)
        assert think.mode == "offline"
        assert "当前没有选中项目" in think.answer

    def test_forced_offline_with_configured_model_reports_the_right_reason(self, tmp_path) -> None:
        settings = make_settings(tmp_path, configured=True)
        chat = ChatClient(settings, client=FakeOpenAI([]), sleep=lambda _: None)
        answer = ask("有哪些项目？", settings, force_offline=True, client=chat)
        assert answer.mode == "offline"
        assert "未配置可用的大模型" not in answer.answer
        assert "force_offline" in answer.answer

    def test_status_reports_offline_mode(self, tmp_path) -> None:
        settings = make_settings(tmp_path)
        payload = status(settings)
        assert payload["mode"] == "offline"
        assert payload["chat"]["configured"] is False
        assert payload["tools"]


class TestLlmLoop:
    def test_tool_then_final_answer(self, tmp_path) -> None:
        settings = make_settings(tmp_path, configured=True)
        seed_project(settings, tmp_path)
        fake = FakeOpenAI([
            response(tool_calls=[tool_call("c1", "project_overview", {})]),
            response("## 结论\n项目共有 0 个事件。"),
        ])
        chat = ChatClient(settings, client=fake, sleep=lambda _: None)
        answer = ask("项目里有什么？", settings, project_id=PROJECT, client=chat, max_steps=3)
        assert answer.mode == "llm"
        assert answer.steps == 2
        assert answer.tool_calls[0]["tool"] == "project_overview"
        assert "结论" in answer.answer
        assert answer.usage["total_tokens"] == 36
        # The second request must carry the tool result back to the model.
        second = fake.chat.completions.calls[1]["messages"]
        assert any(message.get("role") == "tool" for message in second)

    def test_model_failure_falls_back_to_offline(self, tmp_path) -> None:
        settings = make_settings(tmp_path, configured=True)
        seed_project(settings, tmp_path)

        def explode(**kwargs):
            raise ValueError("bad request")

        class Broken:
            def __init__(self):
                self.chat = SimpleNamespace(completions=SimpleNamespace(create=explode))

        chat = ChatClient(settings, client=Broken(), sleep=lambda _: None)
        answer = ask("分析一下", settings, project_id=PROJECT, client=chat, max_steps=2)
        assert answer.mode == "offline"
        assert answer.errors
        assert "结论" in answer.answer


def test_empty_message_rejected(tmp_path) -> None:
    settings = make_settings(tmp_path)
    with pytest.raises(ValueError):
        ask("   ", settings, force_offline=True)


def test_sanitize_removes_provider_template_artifacts() -> None:
    from epitoperank.agent.copilot import _sanitize_model_text

    raw = "## 结论\n正常内容\n<｜｜DSML｜｜ calls>\n<｜｜DSML｜｜ invoke name=\"x\">\n## 局限\nok"
    cleaned = _sanitize_model_text(raw)
    assert "DSML" not in cleaned
    assert "## 结论" in cleaned
    assert "## 局限" in cleaned
    assert _sanitize_model_text("普通回答") == "普通回答"


def test_offline_plan_mode_reports_plan_and_strategy(tmp_path) -> None:
    settings = make_settings(tmp_path)
    seed_project(settings, tmp_path)
    events = []
    answer = ask("比较质量与候选，并给出下一步建议。", settings, project_id=PROJECT,
                 force_offline=True, mode="plan", on_event=events.append)
    assert answer.strategy == "plan"
    assert answer.plan.get("steps")
    assert any(event["event"] == "plan" for event in events)
    assert answer.critique.get("verdict") in {"pass", "revise"}

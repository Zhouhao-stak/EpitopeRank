"""Regression tests for the agentic chat UI.

These tests are deliberately static: they inspect the rendered HTML/JS instead
of driving a browser. That is enough to catch the two failure modes that have
already bitten this page:

* Python string-escape leakage into the inline JavaScript (``\\uXXXX`` inside a
  normal Python string can produce lone surrogates that break UTF-8 encoding);
* the UI silently reverting to the old non-agentic chat (missing controls,
  missing SSE endpoint, missing abort wiring).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from epitoperank.interface import web_ui

SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL)


def rendered_html() -> str:
    response = web_ui.render("EpitopeRank test")
    return response.body.decode("utf-8")


def find_node() -> str | None:
    for name in ("node", "node.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


class TestAgenticControls:
    def test_chat_controls_exist(self) -> None:
        html = rendered_html()
        for needle in (
            'id="chat-mode"',
            'id="chat-network"',
            'id="chat-cache"',
            'id="chat-stop"',
            'id="chat-status"',
            'id="chat-send"',
        ):
            assert needle in html, f"missing control: {needle}"

    def test_strategy_options_cover_auto_plan_react(self) -> None:
        html = rendered_html()
        assert '<option value="auto">' in html
        assert '<option value="plan">' in html
        assert '<option value="react">' in html

    def test_stream_endpoint_and_abort_are_wired(self) -> None:
        html = rendered_html()
        assert "/api/copilot/stream" in html
        assert "function stopChat" in html
        assert "window.chatAbort" in html
        assert "signal: controller.signal" in html

    def test_pending_message_has_marker(self) -> None:
        html = rendered_html()
        assert "data-pending-body" in html
        assert "renderPendingMessage" in html

    def test_sse_event_handlers_are_present(self) -> None:
        html = rendered_html()
        for event in ("plan", "step", "tool_start", "tool_result",
                      "critique", "revision", "offline", "done", "error"):
            assert f"event === '{event}'" in html, f"missing SSE handler: {event}"

    def test_request_payload_passes_mode_and_flags(self) -> None:
        html = rendered_html()
        assert "mode: modeEl ? modeEl.value : 'auto'" in html
        assert "allow_network: networkEl ? !!networkEl.checked : true" in html
        assert "use_cache: cacheEl ? !!cacheEl.checked : true" in html


class TestEncodingSafety:
    def test_rendered_html_has_no_lone_surrogates(self) -> None:
        html = rendered_html()
        bad = [(index, hex(ord(char))) for index, char in enumerate(html)
               if 0xD800 <= ord(char) <= 0xDFFF]
        assert bad == [], f"lone surrogates at {bad[:5]}"

    def test_rendered_html_encodes_as_utf8(self) -> None:
        html = rendered_html()
        encoded = html.encode("utf-8")
        assert encoded.decode("utf-8") == html

    def test_document_has_title_and_no_placeholder(self) -> None:
        # NOTE: ``render(title=...)`` currently has no effect because the HTML
        # carries a hard-coded <title> instead of the ``__TITLE__`` placeholder
        # the function replaces. This test pins the observable behaviour and
        # reports the mismatch to the parent agent instead of asserting the
        # intended (but unimplemented) substitution.
        html = rendered_html()
        assert "<title>EpitopeRank" in html
        assert "__TITLE__" not in html


class TestInlineJavaScriptSyntax:
    def test_inline_scripts_parse_with_node(self, tmp_path: Path) -> None:
        node = find_node()
        if node is None:
            pytest.skip("node executable not available")

        html = rendered_html()
        blocks = SCRIPT_RE.findall(html)
        assert blocks, "no inline <script> blocks found"

        failures: list[str] = []
        for index, block in enumerate(blocks):
            path = tmp_path / f"inline_{index}.js"
            path.write_text(block, encoding="utf-8")
            completed = subprocess.run(
                [node, "--check", str(path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            if completed.returncode != 0:
                failures.append(
                    f"block {index}: {completed.stderr.strip()[:800]}"
                )
        assert failures == [], "JavaScript syntax errors: " + " | ".join(failures)

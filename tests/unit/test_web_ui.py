"""Static regression tests for the rendered web UI.

Driving a browser is not necessary to catch the failure modes that have already
bitten this page:

* Python string-escape leakage into the inline JavaScript (``\\uXXXX`` inside a
  normal Python string can produce lone surrogates that break UTF-8 encoding);
* the settings page losing its controls, or the removed chat assistant being
  wired back in by accident.
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


class TestSettingsPage:
    def test_model_config_and_mcp_console_are_present(self) -> None:
        html = rendered_html()
        for needle in (
            'id="page-settings"',
            'data-page="settings"',
            'id="cfg-base"',
            'id="cfg-model"',
            'id="cfg-key"',
            'id="cfg-save"',
            'id="mcp-panel"',
            'id="mcp-server-select"',
            'id="mcp-call-btn"',
        ):
            assert needle in html, f"missing setting control: {needle}"

    def test_chat_assistant_is_gone(self) -> None:
        html = rendered_html()
        for needle in (
            'id="chat-input"',
            'id="chat-messages"',
            "/api/copilot/stream",
            "sendChatMessage",
            "page-assistant",
        ):
            assert needle not in html, f"leftover chat assistant wiring: {needle}"


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
        # the function replaces. This test pins the observable behaviour.
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

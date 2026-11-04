"""Tests for the copilot tool-result cache."""

from __future__ import annotations

import time

from epitoperank.agent.tool_cache import ToolCache


def test_put_get_and_project_isolation(tmp_path) -> None:
    cache = ToolCache(tmp_path / "cache.sqlite3", ttl=60)
    key = ToolCache.key("P1", "annotate_gene", {"gene": "TP53"})
    other = ToolCache.key("P2", "annotate_gene", {"gene": "TP53"})
    cache.put(key, {"summary": "ok", "data": {"symbol": "TP53"}})
    hit = cache.get(key)
    assert hit is not None
    assert hit.value["data"]["symbol"] == "TP53"
    assert cache.get(other) is None
    assert cache.stats()["entries"] == 1


def test_argument_order_does_not_matter(tmp_path) -> None:
    first = ToolCache.key("P1", "query_events", {"fdr_max": 0.05, "limit": 10})
    second = ToolCache.key("P1", "query_events", {"limit": 10, "fdr_max": 0.05})
    assert first == second


def test_ttl_expiry(tmp_path) -> None:
    cache = ToolCache(tmp_path / "cache.sqlite3", ttl=0.01)
    key = ToolCache.key("P1", "search_literature", {"query": "x"})
    cache.put(key, {"value": 1})
    time.sleep(0.05)
    assert cache.get(key) is None


def test_disabled_cache_is_a_noop(tmp_path) -> None:
    cache = ToolCache(tmp_path / "cache.sqlite3", enabled=False)
    key = ToolCache.key("P1", "x", {})
    cache.put(key, {"value": 1})
    assert cache.get(key) is None
    assert cache.clear() == 0
    assert cache.stats()["enabled"] is False


def test_clear(tmp_path) -> None:
    cache = ToolCache(tmp_path / "cache.sqlite3")
    for index in range(3):
        cache.put(ToolCache.key("P1", "t", {"i": index}), {"value": index})
    assert cache.clear() == 3
    assert cache.stats()["entries"] == 0

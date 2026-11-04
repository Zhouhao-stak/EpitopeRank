"""Persistent, bounded cache for copilot tool results.

Two problems this solves:

* the same gene/literature/enrichment call is repeated across turns and across
  users of the same project, burning API quota and latency;
* a network tool can be slow or flaky, and an agent should not pay that cost
  twice for an identical request.

Design notes
------------
* SQLite (same storage family as the rest of the project), one row per key.
* Keys are ``project | tool | canonical JSON arguments`` hashes, so a cache hit
  can never leak results across projects.
* Only explicitly *cacheable* tools use it; cheap in-memory project reads stay
  uncached so the answer always reflects the current analysis state.
* Every entry has a TTL. Expired rows are removed lazily on read.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass
class CacheHit:
    value: Any
    created_at: float
    age_seconds: float


class ToolCache:
    """Small SQLite-backed TTL cache with explicit enable/disable."""

    def __init__(self, path: str | Path | None, *, ttl: float = 1800.0,
                 enabled: bool = True) -> None:
        self.path = Path(path) if path else None
        self.ttl = float(ttl)
        self.enabled = bool(enabled and self.path)
        self._ready = False

    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection | None:
        if not self.enabled or self.path is None:
            return None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(str(self.path), timeout=10.0)
            # Several uvicorn workers share this cache file; WAL lets readers
            # proceed while one worker writes a fresh tool result.
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=NORMAL")
            except sqlite3.DatabaseError:
                pass  # network filesystem refused WAL; keep the default
            if not self._ready:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS tool_cache ("
                    " key TEXT PRIMARY KEY, value TEXT NOT NULL,"
                    " created_at REAL NOT NULL, ttl REAL NOT NULL, hits INTEGER DEFAULT 0)"
                )
                connection.commit()
                self._ready = True
            return connection
        except (OSError, sqlite3.Error):
            # A broken cache must degrade to "no cache", never to a failed answer.
            self.enabled = False
            return None

    @staticmethod
    def key(project_id: str, tool: str, arguments: Mapping[str, Any]) -> str:
        blob = json.dumps(
            [project_id or "", tool, arguments or {}],
            ensure_ascii=False, sort_keys=True, default=str,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    def get(self, key: str) -> CacheHit | None:
        connection = self._connect()
        if connection is None:
            return None
        try:
            row = connection.execute(
                "SELECT value, created_at, ttl FROM tool_cache WHERE key = ?", (key,)
            ).fetchone()
            if not row:
                return None
            value, created_at, ttl = row
            age = time.time() - float(created_at)
            if age > float(ttl):
                connection.execute("DELETE FROM tool_cache WHERE key = ?", (key,))
                connection.commit()
                return None
            connection.execute("UPDATE tool_cache SET hits = hits + 1 WHERE key = ?", (key,))
            connection.commit()
            return CacheHit(json.loads(value), float(created_at), round(age, 3))
        except (sqlite3.Error, ValueError):
            return None
        finally:
            connection.close()

    def put(self, key: str, value: Any, *, ttl: float | None = None) -> None:
        connection = self._connect()
        if connection is None:
            return
        try:
            connection.execute(
                "INSERT OR REPLACE INTO tool_cache (key, value, created_at, ttl, hits)"
                " VALUES (?, ?, ?, ?, COALESCE((SELECT hits FROM tool_cache WHERE key = ?), 0))",
                (key, json.dumps(value, ensure_ascii=False, default=str),
                 time.time(), float(ttl if ttl is not None else self.ttl), key),
            )
            connection.commit()
        except (sqlite3.Error, TypeError, ValueError):
            pass
        finally:
            connection.close()

    def clear(self) -> int:
        connection = self._connect()
        if connection is None:
            return 0
        try:
            cursor = connection.execute("DELETE FROM tool_cache WHERE 1=1")
            connection.commit()
            return int(cursor.rowcount or 0)
        except sqlite3.Error:
            return 0
        finally:
            connection.close()

    def stats(self) -> dict[str, Any]:
        connection = self._connect()
        if connection is None:
            return {"enabled": False, "entries": 0, "hits": 0}
        try:
            entries, hits = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(hits), 0) FROM tool_cache"
            ).fetchone()
            return {"enabled": True, "path": str(self.path), "entries": int(entries),
                    "hits": int(hits), "ttl_seconds": self.ttl}
        except sqlite3.Error:
            return {"enabled": False, "entries": 0, "hits": 0}
        finally:
            connection.close()

"""Stable, per-user runtime storage.

Why this module exists
----------------------
The runtime root holds everything a user would call "their work":
``epitoperank.sqlite3`` (projects, events, candidates, workflow logs),
``projects/`` (figures, reports, tables), uploaded inputs and neoantigen
sessions.

Historically that root was ``%TEMP%\\epitoperank`` on Windows. Windows Storage
Sense, Disk Cleanup and most "PC cleaner" tools delete ``%TEMP%`` without
asking, so the whole analysis history could vanish between sessions. Frozen
builds also wrote to ``<exe_dir>/epitoperank_runtime``, which produced a second,
independent history next to the executable.

This module fixes both problems:

* :func:`default_runtime_root` returns a *stable* per-user directory that
  neither the OS nor an application update touches.
* :func:`migrate_legacy_storage` merges any pre-existing legacy directory into
  the new one (databases merged row-by-row, project folders copied, artifact
  paths rewritten), so nobody loses the projects they already have.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#: Copied verbatim (recursively) from a legacy root into the new one.
_COPY_DIRS = ("projects", "neoantigen_workflows", "logs")

#: Merged table-by-table when both databases exist.
_DATABASES = ("epitoperank.sqlite3", "literature.sqlite3")

_MARKER = ".storage-migrated.json"
_lock = threading.Lock()


# --------------------------------------------------------------------------
# default location
# --------------------------------------------------------------------------
def default_runtime_root() -> Path:
    """Return the persistent, per-user directory for runtime state.

    Linux/macOS: ``$XDG_DATA_HOME/epitoperank`` (default ``~/.local/share``).
    Windows:     ``%LOCALAPPDATA%\\EpitopeRank``.

    ``/var/tmp`` is deliberately *not* used any more: it is wiped on reboot on
    many distributions, which silently deleted the analysis history.
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "EpitopeRank"
        return Path.home() / "AppData" / "Local" / "EpitopeRank"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "epitoperank"


def _exe_dir() -> Path | None:
    """返回打包后 exe 所在目录；源码运行时返回 None。"""
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except OSError:  # pragma: no cover - defensive
            return None
    return None


def legacy_runtime_roots(target: Path | None = None) -> list[Path]:
    """Return every location older builds may have written state to.

    Ordered from most valuable to least: the desktop bundle directory first
    (that is where the packaged app kept the real projects), then the system
    temp directory used by source runs, then any in-repo ``runtime`` folder.
    """
    target = (target or default_runtime_root()).resolve()
    candidates: list[Path] = []

    import tempfile

    exe_dir = _exe_dir()
    temp_dir = Path(tempfile.gettempdir())

    # The product shipped as "SpliceGAIP" before the rename, so a machine that
    # upgrades in place still has its projects under the old names. Probe both
    # spellings, newest name first.
    for name in ("epitoperank", "splicegaip", "SpliceGAIP"):
        if exe_dir is not None:
            candidates.append(exe_dir / f"{name}_runtime")
        candidates.append(temp_dir / name)
        candidates.append(Path("/var/tmp") / name)

    if os.name == "nt":  # %LOCALAPPDATA%\<old product name>
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            candidates.append(Path(base) / "SpliceGAIP")

    candidates.append(Path.cwd() / "runtime")
    candidates.append(Path.cwd() / "dist" / "epitoperank_runtime")
    candidates.append(Path.cwd() / "dist" / "splicegaip_runtime")

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:  # pragma: no cover - defensive
            continue
        key = str(resolved).lower()
        if key in seen or resolved == target:
            continue
        if not resolved.is_dir():
            continue
        seen.add(key)
        unique.append(resolved)
    return unique


def storage_info(root: Path | None = None) -> dict[str, Any]:
    """Describe the storage layout (used by the UI "data location" panel)."""
    root = (root or default_runtime_root()).resolve()
    databases = {}
    for name in _DATABASES:
        path = root / name
        databases[name] = {
            "path": str(path),
            "exists": path.is_file(),
            "size_mb": round(path.stat().st_size / 1048576, 1) if path.is_file() else 0.0,
        }
    projects_dir = root / "projects"
    return {
        "runtime_root": str(root),
        "databases": databases,
        "projects_dir": str(projects_dir),
        "project_count": len([p for p in projects_dir.iterdir() if p.is_dir()])
        if projects_dir.is_dir()
        else 0,
        "legacy_roots": [str(p) for p in legacy_runtime_roots(root)],
    }


# --------------------------------------------------------------------------
# migration
# --------------------------------------------------------------------------
def _now() -> str:
    """返回秒级精度的 UTC 时间戳字符串，写入迁移标记。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_marker(root: Path) -> dict[str, Any]:
    """读取迁移标记 JSON；文件缺失或内容损坏时返回空字典。"""
    path = root / _MARKER
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_marker(root: Path, payload: dict[str, Any]) -> None:
    """把迁移标记写回运行时目录；目标只读等写入失败时静默忽略。"""
    try:
        root.mkdir(parents=True, exist_ok=True)
        (root / _MARKER).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:  # pragma: no cover - read-only target
        pass


def _table_names(connection: sqlite3.Connection, schema: str = "main") -> list[str]:
    """列出指定 schema 里的普通表名（排除 sqlite_ 开头的内部表）。"""
    rows = connection.execute(
        f"SELECT name FROM {schema}.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [row[0] for row in rows]


def _columns(connection: sqlite3.Connection, table: str, schema: str = "main") -> list[str]:
    """返回指定表的列名列表，顺序与建表语句一致。"""
    rows = connection.execute(f'PRAGMA {schema}.table_info("{table}")').fetchall()
    return [row[1] for row in rows]


def _merge_sqlite(target: Path, source: Path) -> dict[str, int]:
    """Merge ``source`` into ``target`` without clobbering existing rows.

    Tables are matched by name; only columns present in both sides are copied,
    and ``INSERT OR IGNORE`` keeps the primary keys already in ``target``. The
    operation is safe to run twice (rows that already exist are skipped).
    """
    stats = {"tables": 0, "rows": 0}
    if not source.is_file():
        return stats
    target.parent.mkdir(parents=True, exist_ok=True)

    if not target.is_file() or target.stat().st_size == 0:
        shutil.copy2(source, target)
        stats["tables"] = 1
        return stats

    try:
        source_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30)
    except sqlite3.Error:
        return stats

    target_conn = sqlite3.connect(target, timeout=60)
    attached = False
    try:
        source_schemas = {
            table: source_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            for table in _table_names(source_conn)
        }
        target_conn.execute("ATTACH DATABASE ? AS legacy", (str(source),))
        attached = True
        for table, row in source_schemas.items():
            create_sql = row[0] if row else None
            if not create_sql:
                continue
            existing = set(_table_names(target_conn))
            if table not in existing:
                target_conn.execute(create_sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1))
            source_columns = _columns(target_conn, table, "legacy")
            target_columns = set(_columns(target_conn, table))
            shared = [column for column in source_columns if column in target_columns]
            # ``id`` is an AUTOINCREMENT surrogate key on log-like tables. Copying
            # it verbatim makes every row of the second database collide with the
            # first and get skipped — let SQLite assign fresh ids instead.
            if "AUTOINCREMENT" in create_sql.upper() and "id" in shared:
                shared = [column for column in shared if column != "id"]
            if not shared:
                continue
            column_list = ", ".join(f'"{column}"' for column in shared)
            try:
                cursor = target_conn.execute(
                    f'INSERT OR IGNORE INTO main."{table}" ({column_list}) '
                    f'SELECT {column_list} FROM legacy."{table}"'
                )
                stats["tables"] += 1
                stats["rows"] += max(cursor.rowcount, 0)
            except sqlite3.Error:
                continue
        target_conn.commit()
    finally:
        if attached:
            try:
                target_conn.execute("DETACH DATABASE legacy")
            except sqlite3.Error:
                pass
        target_conn.close()
        source_conn.close()
    return stats


def _copy_tree(source: Path, target: Path) -> int:
    """把源目录下的文件与子目录逐个复制到目标目录，已存在的同名项跳过，返回复制条目数。"""
    if not source.is_dir():
        return 0
    copied = 0
    for entry in source.iterdir():
        destination = target / entry.name
        try:
            if entry.is_dir():
                if destination.exists():
                    continue
                shutil.copytree(entry, destination)
                copied += 1
            elif entry.is_file() and not destination.exists():
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry, destination)
                copied += 1
        except OSError:
            continue
    return copied


def _rewrite_artifact_paths(database: Path, old_root: Path, new_root: Path) -> int:
    """Point stored artifact paths at the migrated location."""
    if not database.is_file():
        return 0
    connection = sqlite3.connect(database, timeout=60)
    try:
        tables = set(_table_names(connection))
        if "artifacts" not in tables:
            return 0
        cursor = connection.execute(
            "UPDATE artifacts SET path = REPLACE(path, ?, ?) WHERE path LIKE ?",
            (str(old_root), str(new_root), str(old_root) + "%"),
        )
        connection.commit()
        return max(cursor.rowcount, 0)
    except sqlite3.Error:
        return 0
    finally:
        connection.close()


def migrate_legacy_storage(
    target: Path | None = None,
    *,
    force: bool = False,
    logger: Any = None,
) -> dict[str, Any]:
    """Merge every legacy runtime directory into ``target`` (idempotent).

    Returns a report describing what was moved, so the UI and the startup
    banner can tell the user where their old projects went.
    """
    target = (target or default_runtime_root()).resolve()
    with _lock:
        marker = _read_marker(target)
        done = set(marker.get("migrated_from", []))
        report: dict[str, Any] = {
            "target": str(target),
            "migrated_from": [],
            "databases": {},
            "directories": {},
            "artifacts_rewritten": 0,
        }

        for source in legacy_runtime_roots(target):
            key = str(source)
            if key in done and not force:
                continue
            if not any((source / name).exists() for name in _DATABASES + _COPY_DIRS):
                continue

            target.mkdir(parents=True, exist_ok=True)
            for name in _DATABASES:
                source_db = source / name
                if not source_db.is_file():
                    continue
                stats = _merge_sqlite(target / name, source_db)
                report["databases"].setdefault(name, {"tables": 0, "rows": 0})
                report["databases"][name]["tables"] += stats["tables"]
                report["databases"][name]["rows"] += stats["rows"]
                if name == "epitoperank.sqlite3":
                    report["artifacts_rewritten"] += _rewrite_artifact_paths(
                        target / name, source, target
                    )

            for name in _COPY_DIRS:
                copied = _copy_tree(source / name, target / name)
                if copied:
                    report["directories"].setdefault(name, 0)
                    report["directories"][name] += copied

            for entry in source.glob("epitoperank_upload_*"):
                if entry.is_dir():
                    destination = target / entry.name
                    if not destination.exists():
                        try:
                            shutil.copytree(entry, destination)
                            report["directories"].setdefault("uploads", 0)
                            report["directories"]["uploads"] += 1
                        except OSError:
                            pass

            done.add(key)
            report["migrated_from"].append(key)
            if logger is not None:
                try:
                    logger(f"storage: migrated legacy runtime from {source}")
                except Exception:  # noqa: BLE001 - logging must never break migration
                    pass

        _write_marker(
            target,
            {"migrated_from": sorted(done), "updated_at": _now()},
        )
        return report

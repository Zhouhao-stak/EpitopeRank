"""Tests for the stable runtime-storage layer (migration included)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from splicegaip import storage


SCHEMA = """
CREATE TABLE projects (project_id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL
);
"""


def _make_db(path: Path, projects: list[tuple[str, str]], artifacts: list[tuple[str, str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        connection.executemany("INSERT INTO projects VALUES (?, ?, '2026-01-01')", projects)
        connection.executemany("INSERT INTO artifacts (project_id, kind, path) VALUES (?, ?, ?)", artifacts)
        connection.commit()
    finally:
        connection.close()
    return path


def _rows(path: Path, table: str, order: str = "1") -> list[tuple]:
    connection = sqlite3.connect(path)
    try:
        return connection.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
    finally:
        connection.close()


def test_default_runtime_root_is_not_a_temp_directory(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\tester\AppData\Local")
    monkeypatch.setattr(storage.os, "name", "nt")
    root = storage.default_runtime_root()
    assert root == Path(r"C:\Users\tester\AppData\Local") / "SpliceGAIP"
    assert "Temp" not in str(root)


def test_merge_keeps_artifacts_from_both_databases(tmp_path):
    """The AUTOINCREMENT id must not make the second database's rows collide."""
    target = _make_db(
        tmp_path / "target.sqlite3",
        [("P1", "first")],
        [("P1", "figure:volcano", "/old/P1/volcano.png")],
    )
    source = _make_db(
        tmp_path / "source.sqlite3",
        [("P2", "second")],
        [("P2", "figure:volcano", "/old/P2/volcano.png"), ("P2", "report:html", "/old/P2/report.html")],
    )

    stats = storage._merge_sqlite(target, source)

    assert stats["tables"] == 2
    projects = _rows(target, "projects", "project_id")
    assert [row[0] for row in projects] == ["P1", "P2"]
    artifacts = _rows(target, "artifacts", "id")
    assert len(artifacts) == 3
    # ids are re-assigned by SQLite, so they stay unique
    assert len({row[0] for row in artifacts}) == 3


def test_merge_is_idempotent_for_primary_keyed_rows(tmp_path):
    target = _make_db(tmp_path / "target.sqlite3", [("P1", "first")], [])
    source = _make_db(tmp_path / "source.sqlite3", [("P1", "first")], [])

    storage._merge_sqlite(target, source)
    storage._merge_sqlite(target, source)

    assert len(_rows(target, "projects")) == 1


def test_merge_copies_the_database_when_target_is_absent(tmp_path):
    source = _make_db(tmp_path / "source.sqlite3", [("P1", "first")], [])
    target = tmp_path / "target.sqlite3"

    storage._merge_sqlite(target, source)

    assert target.is_file()
    assert [row[0] for row in _rows(target, "projects")] == ["P1"]


def test_migrate_legacy_storage_copies_projects_and_rewrites_paths(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy-root"
    _make_db(
        legacy / "splicegaip.sqlite3",
        [("P1", "first")],
        [("P1", "figure:volcano", str(legacy / "projects" / "P1" / "figures" / "volcano.png"))],
    )
    (legacy / "projects" / "P1" / "figures").mkdir(parents=True)
    (legacy / "projects" / "P1" / "figures" / "volcano.png").write_bytes(b"png")
    target = tmp_path / "new-root"

    monkeypatch.setattr(storage, "legacy_runtime_roots", lambda _target=None: [legacy])

    report = storage.migrate_legacy_storage(target)

    assert report["migrated_from"] == [str(legacy.resolve())]
    assert (target / "splicegaip.sqlite3").is_file()
    assert (target / "projects" / "P1" / "figures" / "volcano.png").is_file()
    artifact_path = _rows(target / "splicegaip.sqlite3", "artifacts")[0][3]
    assert artifact_path.startswith(str(target.resolve()))
    assert str(legacy) not in artifact_path


def test_migration_runs_only_once(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy-root"
    _make_db(legacy / "splicegaip.sqlite3", [("P1", "first")], [])
    target = tmp_path / "new-root"
    monkeypatch.setattr(storage, "legacy_runtime_roots", lambda _target=None: [legacy])

    first = storage.migrate_legacy_storage(target)
    second = storage.migrate_legacy_storage(target)

    assert first["migrated_from"]
    assert second["migrated_from"] == []
    assert len(_rows(target / "splicegaip.sqlite3", "projects")) == 1


def test_storage_info_reports_layout(tmp_path):
    root = tmp_path / "root"
    _make_db(root / "splicegaip.sqlite3", [("P1", "first")], [])
    (root / "projects" / "P1").mkdir(parents=True)

    info = storage.storage_info(root)

    assert info["runtime_root"] == str(root.resolve())
    assert info["databases"]["splicegaip.sqlite3"]["exists"] is True
    assert info["project_count"] == 1

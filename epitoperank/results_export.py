"""Publish each project's deliverables into one human-readable folder.

The runtime directory (``%LOCALAPPDATA%\\EpitopeRank`` on Windows) keeps the
database and intermediate state, but it is a poor place for a user to browse:
folder names are opaque ``SPN-XXXXXXXX`` ids and everything sits under AppData.

After a run finishes we therefore copy the deliverables the user actually cares
about into ``<results_root>/<项目名>_<短ID>/``:

    report.html / report.pdf
    figures/*.png,*.svg
    neoantigen_results/         (when the project produced peptides)
    项目说明.txt                 (what this folder is, how big the run was)

Copies are idempotent: re-running a project refreshes its folder in place.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Iterable

#: Folder that receives one sub-directory per project.
RESULTS_DIRNAME = "results"

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def default_results_root(project_root: Path) -> Path:
    """Where exported bundles live, overridable with ``EPITOPERANK_RESULTS_ROOT``.

    In a frozen desktop build ``project_root`` is the temporary unpack
    directory (``_MEIPASS``), which is deleted on exit — so the bundles must go
    next to the ``.exe`` instead, where the user can actually find them.
    """
    override = os.getenv("EPITOPERANK_RESULTS_ROOT", "").strip()
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent / RESULTS_DIRNAME
        except OSError:  # pragma: no cover - defensive
            pass
    return Path(project_root) / RESULTS_DIRNAME


def safe_folder_name(name: str, project_id: str, *, limit: int = 60) -> str:
    """A readable folder name that survives Explorer, plus the id for uniqueness."""
    cleaned = _ILLEGAL.sub("_", str(name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    if not cleaned:
        cleaned = "未命名项目"
    if len(cleaned) > limit:
        cleaned = cleaned[:limit].rstrip(" ._")
    return f"{cleaned}_{project_id}"


def _copy_tree(source: Path, target: Path) -> int:
    """Copy a directory into ``target`` (merging), returning the file count."""
    copied = 0
    if not source.is_dir():
        return 0
    target.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        if entry.is_dir():
            copied += _copy_tree(entry, target / entry.name)
        elif entry.is_file():
            shutil.copy2(entry, target / entry.name)
            copied += 1
    return copied


def _candidate_sources(project_dir: Path, input_dir: Path | None) -> Iterable[tuple[str, Path]]:
    """Yield (label, path) pairs of everything worth showing the user."""
    for name in ("report.html", "report.pdf"):
        path = project_dir / name
        if path.is_file():
            yield name, path
    for sub in ("figures", "tables"):
        path = project_dir / sub
        if path.is_dir():
            yield sub, path
    # Peptide runs write next to the source data rather than in the runtime dir.
    for base in (project_dir, input_dir):
        if base is None:
            continue
        for name in ("neoantigen_results", "peptide_results"):
            path = base / name
            if path.is_dir() and not any(path.name == seen for seen, _ in []):
                yield name, path


def _manifest_text(
    project_name: str,
    project_id: str,
    stats: dict[str, Any],
    project_dir: Path,
) -> str:
    lines = [
        f"项目名称：{project_name or '未命名项目'}",
        f"项目编号：{project_id}",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "本文件夹是本项目的交付成果，可直接打包发给同事或存档。",
        "",
        "包含内容：",
        "  report.html / report.pdf  完整分析报告（浏览器可直接打开）",
        "  figures/                  报告里的图，PNG 可插入 PPT，SVG 可无损放大",
        "  neoantigen_results/       候选肽与 HLA 预测结果（如本项目生成过）",
        "",
    ]
    for key, label in (
        ("sample_count", "样本数"),
        ("event_count", "剪接事件数"),
        ("significant_count", "显著事件数"),
    ):
        value = stats.get(key)
        if value is not None:
            lines.append(f"{label}：{value}")
    lines += [
        "",
        f"原始运行目录（含中间文件，可清理）：{project_dir}",
        "删除本文件夹不会影响系统，重新跑一次分析会再次生成。",
    ]
    return "\n".join(lines) + "\n"


def export_bundle(
    project_dir: str | Path,
    project_name: str,
    project_id: str,
    *,
    results_root: str | Path,
    stats: dict[str, Any] | None = None,
    input_dir: str | Path | None = None,
) -> Path | None:
    """Copy deliverables to ``results_root/<name>_<id>/`` and return that path."""
    project_path = Path(project_dir)
    if not project_path.is_dir():
        return None

    target = Path(results_root) / safe_folder_name(project_name, project_id)
    target.mkdir(parents=True, exist_ok=True)

    copied = 0
    seen: set[str] = set()
    for label, source in _candidate_sources(
        project_path, Path(input_dir) if input_dir else None
    ):
        if label in seen:
            continue
        seen.add(label)
        if source.is_dir():
            copied += _copy_tree(source, target / label)
        else:
            shutil.copy2(source, target / label)
            copied += 1

    if not copied:
        return None

    (target / "项目说明.txt").write_text(
        _manifest_text(project_name, project_id, stats or {}, project_path),
        encoding="utf-8",
    )
    return target


def package_bundle(bundle_dir: str | Path, *, dest: str | Path | None = None) -> Path | None:
    """Zip a results bundle so it can be mailed, archived or uploaded."""
    import zipfile

    folder = Path(bundle_dir)
    if not folder.is_dir():
        return None
    archive = Path(dest) if dest else folder.with_suffix(".zip")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(folder).as_posix())
    return archive


def cloud_upload_target() -> tuple[str, str]:
    """Return ``(url, token)`` for the configured cloud receiver, or empty strings.

    Set ``EPITOPERANK_CLOUD_URL`` (e.g. ``http://<server>:8800/api/cloud/upload``)
    and optionally ``EPITOPERANK_CLOUD_TOKEN``. With no URL, projects stay local.
    """
    url = os.getenv("EPITOPERANK_CLOUD_URL", "").strip()
    token = os.getenv("EPITOPERANK_CLOUD_TOKEN", "").strip()
    return url, token


def upload_bundle(archive: str | Path, *, timeout: float = 120.0) -> dict[str, Any]:
    """POST a bundle zip to the configured cloud endpoint.

    Returns ``{"ok": bool, "url": str, "detail": str}``; never raises, because a
    cloud failure must not cost the user a finished analysis.
    """
    import urllib.error
    import urllib.request

    url, token = cloud_upload_target()
    if not url:
        return {"ok": False, "url": "", "detail": "未配置云端地址（EPITOPERANK_CLOUD_URL）"}
    path = Path(archive)
    if not path.is_file():
        return {"ok": False, "url": "", "detail": "没有可上传的成果包"}

    boundary = "----epitoperank" + os.urandom(8).hex()
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        "Content-Type: application/zip\r\n\r\n"
    ).encode()
    body += path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()

    request = urllib.request.Request(
        url,
        data=bytes(body),
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", "replace")
        return {"ok": True, "url": url, "detail": payload[:400]}
    except urllib.error.HTTPError as error:
        return {"ok": False, "url": url, "detail": f"HTTP {error.code}"}
    except Exception as error:  # noqa: BLE001 - network errors are all alike here
        return {"ok": False, "url": url, "detail": str(error)[:200]}

"""FastAPI application: upload / analyze / status / report."""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from epitoperank.analysis import extra_figures
from epitoperank.config import ensure_runtime_dirs, load_prepared_settings
from epitoperank.interface.web_ui import render as render_web_ui
from epitoperank.pipeline import list_projects, project_status, run_analysis
from epitoperank.observability import (
    configure_logging,
    new_request_id,
    reset_request_id,
    set_request_id,
)

API_VERSION = "0.1.0"
logger = logging.getLogger(__name__)

#: Remembered CDS column mappings, stored next to the table it describes.
CDS_MAPPING_FILE = ".cds_mapping.json"

# Dark ocean tile with the teal helix + purple AI node, matching the app icon.
# Served as a real endpoint because browsers probe /favicon.ico unconditionally
# and a 404 there shows up as a console error.
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<defs>'
    '<linearGradient id="p" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#0e3240"/><stop offset="1" stop-color="#04101a"/>'
    "</linearGradient>"
    '<linearGradient id="s" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#c8fff6"/><stop offset="1" stop-color="#2dd4bf"/>'
    "</linearGradient>"
    "</defs>"
    '<rect width="32" height="32" rx="7" fill="url(#p)"/>'
    '<path d="M10.50 5.25L10.61 5.70L10.94 6.15L11.47 6.59L12.18 7.04L13.05 7.49L14.04 7.94'
    "L15.10 8.39L16.21 8.83L17.30 9.28L18.34 9.73L19.29 10.18L20.10 10.62L20.75 11.07L21.21 11.52"
    "L21.46 11.97L21.48 12.42L21.29 12.86L20.89 13.31L20.28 13.76L19.51 14.21L18.59 14.66L17.57 15.10"
    "L16.49 15.55L15.38 16.00L14.31 16.45L13.29 16.90L12.39 17.34L11.64 17.79L11.06 18.24L10.67 18.69"
    "L10.51 19.14L10.56 19.58L10.83 20.03L11.32 20.48L11.99 20.93L12.82 21.38L13.78 21.82L14.83 22.27"
    "L15.92 22.72L17.02 23.17L18.08 23.61L19.06 24.06L19.91 24.51L20.60 24.96L21.11 25.41L21.41 25.85"
    'L21.50 26.30L21.36 26.75" fill="none" stroke="#11837d" stroke-width="2.6" stroke-linecap="round"/>'
    '<path d="M21.50 5.25L21.39 5.70L21.06 6.15L20.53 6.59L19.82 7.04L18.95 7.49L17.96 7.94'
    "L16.90 8.39L15.79 8.83L14.70 9.28L13.66 9.73L12.71 10.18L11.90 10.62L11.25 11.07L10.79 11.52"
    "L10.54 11.97L10.52 12.42L10.71 12.86L11.11 13.31L11.72 13.76L12.49 14.21L13.41 14.66L14.43 15.10"
    "L15.51 15.55L16.62 16.00L17.69 16.45L18.71 16.90L19.61 17.34L20.36 17.79L20.94 18.24L21.33 18.69"
    "L21.49 19.14L21.44 19.58L21.17 20.03L20.68 20.48L20.01 20.93L19.18 21.38L18.22 21.82L17.17 22.27"
    "L16.08 22.72L14.98 23.17L13.92 23.61L12.94 24.06L12.09 24.51L11.40 24.96L10.89 25.41L10.59 25.85"
    'L10.50 26.30L10.64 26.75" fill="none" stroke="url(#s)" stroke-width="2.6" stroke-linecap="round"/>'
    '<circle cx="16" cy="15.75" r="2.6" fill="none" stroke="#c4b5fd" stroke-opacity=".7" stroke-width=".8"/>'
    '<circle cx="16" cy="15.75" r="1.7" fill="#a855f7"/>'
    '<circle cx="15.5" cy="15.25" r=".55" fill="#fff"/>'
    "</svg>"
)


def _with_overrides(settings: Any, thresholds: Any) -> Any:
    """Return settings with optional per-request analysis thresholds applied.

    The UI exposes FDR / |delta PSI| / min reads / min samples / top-N as
    "advanced parameters"; anything not supplied keeps the configured value.
    """
    if not isinstance(thresholds, dict) or not thresholds:
        return settings
    import dataclasses

    analysis = settings.analysis
    mapping = {
        "fdr": "fdr_threshold",
        "fdr_threshold": "fdr_threshold",
        "delta_psi": "delta_psi_threshold",
        "delta_psi_threshold": "delta_psi_threshold",
        "min_support_reads": "min_support_reads",
        "min_valid_samples": "min_valid_samples",
        "top_candidates": "top_candidates",
        "enrichment_alpha": "enrichment_alpha",
    }
    changes: dict[str, Any] = {}
    casters = {
        "fdr_threshold": float,
        "delta_psi_threshold": float,
        "min_support_reads": int,
        "min_valid_samples": int,
        "top_candidates": int,
        "enrichment_alpha": float,
    }
    for key, value in thresholds.items():
        field = mapping.get(str(key))
        if field is None or value in (None, ""):
            continue
        try:
            changes[field] = casters[field](value)  # type: ignore[operator]
        except (TypeError, ValueError):
            continue
    if not changes:
        return settings
    new_analysis = dataclasses.replace(analysis, **changes)
    return dataclasses.replace(settings, analysis=new_analysis)


def _export_project_bundle(
    settings: Any,
    project_id: str,
    project_name: str,
    *,
    input_dir: str | None = None,
) -> str:
    """Copy a finished project's deliverables into its own browsable folder.

    Users should not have to dig through ``%LOCALAPPDATA%`` to find a report, so
    every run also publishes ``results/<项目名>_<ID>/``. Failure here must never
    fail the analysis itself: the run's own output directory is still valid.
    """
    from epitoperank.config import PROJECT_ROOT
    from epitoperank.memory.project_memory import ProjectMemory
    from epitoperank.results_export import default_results_root, export_bundle

    project_dir = settings.paths.runtime_root / "projects" / project_id
    stats: dict[str, Any] = {}
    try:
        for row in ProjectMemory(settings.paths.memory_db).list_projects_with_stats():
            if row.get("project_id") == project_id:
                stats = row
                break
    except Exception:  # noqa: BLE001 - stats are cosmetic
        logger.debug("Could not load stats for %s", project_id, exc_info=True)

    try:
        target = export_bundle(
            project_dir,
            project_name or stats.get("name") or project_id,
            project_id,
            results_root=default_results_root(PROJECT_ROOT),
            stats=stats,
            input_dir=input_dir,
        )
    except OSError:
        logger.warning("Could not publish results bundle for %s", project_id, exc_info=True)
        return ""
    return str(target) if target else ""


def create_app() -> FastAPI:
    """Build the EpitopeRank API application."""
    # Load .env file so API keys are available in environment variables
    from epitoperank.llm.envfile import load_env_values
    load_env_values()

    app = FastAPI(title="EpitopeRank API", version=API_VERSION)
    settings, storage_warnings = load_prepared_settings()
    ensure_runtime_dirs(settings)

    # Merge any pre-0.2 runtime directory (system temp dir or the folder next
    # to the executable) into the stable per-user root. Without this, projects
    # analysed by an older build would silently disappear from the UI.
    storage_migration: dict[str, Any] = {"migrated_from": []}
    if not os.getenv("EPITOPERANK_RUNTIME_ROOT", "").strip():
        try:
            from epitoperank.storage import migrate_legacy_storage

            storage_migration = migrate_legacy_storage(
                settings.paths.runtime_root, logger=logger.info
            )
            if storage_migration.get("migrated_from"):
                logger.warning(
                    "Merged legacy runtime storage into %s (sources: %s)",
                    settings.paths.runtime_root,
                    ", ".join(storage_migration["migrated_from"]),
                )
        except Exception as error:  # noqa: BLE001 - never block boot
            logger.warning("Legacy storage migration skipped: %s", error)

    # The built-in MCP tool server runs in-process so the AI assistant always
    # has a live tool provider, including in the packaged one-file build.
    try:
        from epitoperank.mcp.demo_server import ensure_demo_server

        demo_status = ensure_demo_server()
        if demo_status.get("running"):
            logger.info("Built-in MCP server listening on %s", demo_status.get("url"))
        else:
            logger.warning("Built-in MCP server unavailable: %s", demo_status.get("error"))
    except Exception as error:  # noqa: BLE001 - MCP must never block boot
        logger.warning("Built-in MCP server failed to start: %s", error)
    log_path = os.getenv("EPITOPERANK_LOG_FILE") or (
        settings.paths.runtime_root / "logs" / "epitoperank.log"
    )
    configure_logging(log_path)
    configured_api_key = os.getenv("EPITOPERANK_API_KEY", "").strip()
    try:
        configured_rate_limit = max(0, int(os.getenv("EPITOPERANK_RATE_LIMIT", "0")))
    except ValueError:
        configured_rate_limit = 0
    rate_state: dict[str, tuple[float, int]] = {}
    rate_lock = threading.Lock()

    @app.get("/")
    def index() -> Any:
        """Serve the browser UI (what the desktop exe opens automatically)."""
        return render_web_ui(f"EpitopeRank v{API_VERSION}")

    @app.get("/assets/opencc-cn2t.js", include_in_schema=False)
    def traditional_chinese_converter() -> FileResponse:
        """Serve the bundled, offline Chinese script converter."""
        converter = Path(__file__).resolve().parent.parent / "interface" / "opencc-cn2t.js"
        return FileResponse(converter, media_type="application/javascript")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(content=_FAVICON_SVG, media_type="image/svg+xml")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": API_VERSION, "llm_configured": settings.llm.configured}

    @app.middleware("http")
    async def request_boundary(request: Request, call_next: Any) -> Response:
        """Apply request correlation, baseline headers, and optional API auth."""
        request_id = new_request_id(request.headers.get("X-Request-ID"))
        token = set_request_id(request_id)
        started = time.perf_counter()
        response: Response
        try:
            protected = request.url.path.startswith("/api/") and request.url.path != (
                "/api/health"
            )
            rate_limited = False
            if configured_rate_limit and protected:
                client_id = request.client.host if request.client else "unknown"
                now = time.monotonic()
                with rate_lock:
                    window_start, count = rate_state.get(client_id, (now, 0))
                    if now - window_start >= 60:
                        window_start, count = now, 0
                    if count >= configured_rate_limit:
                        rate_limited = True
                        retry_after = max(1, int(60 - (now - window_start)) + 1)
                    else:
                        rate_state[client_id] = (window_start, count + 1)
            if rate_limited:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
            elif configured_api_key and protected:
                supplied = request.headers.get("X-API-Key", "")
                authorization = request.headers.get("Authorization", "")
                if not supplied and authorization.lower().startswith("bearer "):
                    supplied = authorization[7:].strip()
                if not secrets.compare_digest(supplied, configured_api_key):
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "API authentication required"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
        except Exception:
            logger.exception("request_failed", extra={"event": "request_failed"})
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            # The response is intentionally logged only after call_next returns;
            # rejected requests are still observable without logging credentials.
            if "response" in locals():
                logger.info(
                    "request_completed",
                    extra={
                        "event": "request_completed",
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
            reset_request_id(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    def _fresh_settings() -> Any:
        """Reload settings so a key saved through /api/llm/config is live.

        ``settings`` captured above would otherwise keep the credentials the
        process started with, which makes "paste the key in the UI" look like
        it silently failed.
        """
        from epitoperank.config import load_settings

        try:
            return load_settings()
        except Exception:  # noqa: BLE001 - keep the boot-time settings
            return settings

    @app.get("/api/llm/status")
    def llm_status_endpoint() -> dict[str, Any]:
        """Is a model endpoint configured, and what may it enrich?"""
        from epitoperank.llm.enrich import llm_status
        from epitoperank.llm.envfile import env_config_payload

        payload = llm_status(_fresh_settings())
        payload["config"] = env_config_payload()
        return payload

    @app.post("/api/llm/config")
    def llm_config(payload: dict[str, Any]) -> dict[str, Any]:
        """Save model credentials into the local ``.env`` file.

        Accepts ``{"values": {...}}`` or the flat form (``{"MODEL_API_KEY":
        "sk-..."}``). A preset id may be merged in first with
        ``{"preset": "deepseek-flash"}``. Secrets never leave this machine and
        only a masked copy is returned.
        """
        from epitoperank.llm.envfile import PRESETS, write_env_values

        updates: dict[str, str] = {}
        preset = str(payload.get("preset", "")).strip()
        if preset:
            chosen = PRESETS.get(preset)
            if chosen is None:
                raise HTTPException(status_code=400, detail=f"unknown preset: {preset}")
            updates.update({k: v for k, v in chosen.items() if k != "label"})
        raw = payload.get("values")
        if isinstance(raw, dict):
            updates.update({str(key): str(value) for key, value in raw.items()})
        else:
            updates.update({
                str(key): str(value) for key, value in payload.items() if key not in ("preset", "values")
            })
        if not updates:
            raise HTTPException(status_code=400, detail="no configuration values supplied")
        try:
            path, changed = write_env_values(updates)
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"cannot write .env: {error}") from error
        from epitoperank.llm.enrich import llm_status
        from epitoperank.llm.envfile import env_config_payload

        return {
            "saved": True,
            "path": str(path),
            "updated": changed,
            "status": llm_status(_fresh_settings()),
            "config": env_config_payload(),
        }

    @app.get("/api/copilot/tools")
    def copilot_tools_endpoint(project_id: str = "", allow_network: bool = True) -> dict[str, Any]:
        """Describe the tool-using analysis copilot and its readiness."""
        from epitoperank.agent.copilot import status

        return status(_fresh_settings(), project_id=project_id or None,
                      allow_network=allow_network)

    def _copilot_request(payload: dict[str, Any]) -> dict[str, Any]:
        """Validate the shared body of /chat and /stream."""
        message = str(payload.get("message") or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        if len(message) > 8000:
            raise HTTPException(status_code=413, detail="message is too long (max 8000 characters)")
        history = payload.get("history")
        if history is not None and not isinstance(history, list):
            raise HTTPException(status_code=422, detail="history must be a list")
        if isinstance(history, list) and len(history) > 20:
            history = history[-20:]
        try:
            max_steps = max(1, min(10, int(payload.get("max_steps") or 6)))
        except (TypeError, ValueError):
            max_steps = 6
        mode = str(payload.get("mode") or "auto").lower()
        if mode not in {"auto", "react", "plan"}:
            raise HTTPException(status_code=422, detail="mode must be auto, react or plan")
        return {
            "message": message,
            "history": history,
            "project_id": str(payload.get("project_id") or "").strip() or None,
            "max_steps": max_steps,
            "mode": mode,
            "allow_network": bool(payload.get("allow_network", True)),
            "use_cache": bool(payload.get("use_cache", True)),
            "force_offline": bool(payload.get("force_offline")),
        }

    @app.post("/api/copilot/chat")
    def copilot_chat(payload: dict[str, Any]) -> dict[str, Any]:
        """Answer an analyst question with bounded tool use.

        This is the modern agent loop: native function calling over
        project-scoped read-only tools, with a step/tool budget, optional
        plan/critic orchestration, persistent caching and numeric grounding of
        the final answer. Without a model it returns a deterministic briefing
        and says so.
        """
        from epitoperank.agent.copilot import ask

        request = _copilot_request(payload)
        try:
            answer = ask(
                request["message"],
                _fresh_settings(),
                project_id=request["project_id"],
                history=request["history"],
                max_steps=request["max_steps"],
                force_offline=request["force_offline"],
                mode=request["mode"],
                allow_network=request["allow_network"],
                use_cache=request["use_cache"],
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=502, detail=f"copilot failed: {error}") from error
        return answer.as_dict()

    @app.post("/api/copilot/stream")
    def copilot_stream(payload: dict[str, Any]) -> StreamingResponse:
        """Server-Sent Events variant of /chat.

        Events: ``plan``, ``step``, ``tool_start``, ``tool_result``,
        ``critique``, ``revision``, ``final``, ``done`` or ``error``.
        Closing the connection cancels the loop at the next step boundary.
        """
        import queue

        from epitoperank.agent.copilot import ask

        request = _copilot_request(payload)
        events: "queue.Queue[dict[str, Any] | None]" = queue.Queue()
        cancelled = threading.Event()

        def worker() -> None:
            try:
                answer = ask(
                    request["message"],
                    _fresh_settings(),
                    project_id=request["project_id"],
                    history=request["history"],
                    max_steps=request["max_steps"],
                    force_offline=request["force_offline"],
                    mode=request["mode"],
                    allow_network=request["allow_network"],
                    use_cache=request["use_cache"],
                    on_event=events.put,
                    cancel=cancelled.is_set,
                )
                events.put({"event": "done", "data": answer.as_dict()})
            except Exception as error:  # noqa: BLE001 - reported as an SSE error event
                events.put({"event": "error",
                            "data": {"message": f"{type(error).__name__}: {str(error)[:400]}"}})
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True, name="copilot-stream").start()

        def generate():
            try:
                while True:
                    item = events.get()
                    if item is None:
                        break
                    yield (f"event: {item['event']}\n"
                           f"data: {json.dumps(item['data'], ensure_ascii=False, default=str)}\n\n")
            finally:
                cancelled.set()

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                     "X-Accel-Buffering": "no"},
        )

    @app.post("/api/understand")
    def understand(payload: dict[str, Any]) -> dict[str, Any]:
        """Resolve a natural-language question into a structured intent.

        Model-based when an endpoint is configured, rule-based otherwise,
        so the UI can show the same panel in both modes.
        """
        query = str(payload.get("query", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        from epitoperank.llm.enrich import build_enhancer
        from epitoperank.llm.tasks import understand_query

        facts = payload.get("facts") if isinstance(payload.get("facts"), dict) else None
        try:
            from epitoperank.llm.enrich import build_enhancer

            enhancer = build_enhancer(_fresh_settings())
            result = understand_query(query, enhancer=enhancer, facts=facts)
            # Surface why the model path was skipped: without this the UI shows
            # a perfectly reasonable rule-based answer and the user cannot tell
            # that their key / endpoint is not actually working.
            if isinstance(result, dict) and result.get("source") != "llm" and enhancer.errors:
                result["llm_errors"] = enhancer.errors[-3:]
            return result
        except Exception as error:  # noqa: BLE001 - degrade to the rule baseline
            from epitoperank.llm.tasks import classify_query_fallback

            fallback = classify_query_fallback(query, error=str(error))
            fallback["llm_errors"] = [{"feature": "understand", "error": str(error)}]
            return fallback

    @app.get("/api/projects")
    def projects() -> dict[str, Any]:
        return {"projects": list_projects(settings)}

    @app.get("/api/storage")
    def storage() -> dict[str, Any]:
        """Where the app keeps its data, so the user can back it up."""
        from epitoperank.storage import storage_info

        info = storage_info(settings.paths.runtime_root)
        info["memory_db"] = str(settings.paths.memory_db)
        info["literature_db"] = str(settings.paths.literature_db)
        info["migration"] = storage_migration
        return info

    @app.get("/api/status/{project_id}")
    def status(project_id: str) -> dict[str, Any]:
        payload = project_status(project_id, settings)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        return payload

    @app.get("/api/projects/{project_id}/events")
    def project_events(
        project_id: str,
        page: int = 1,
        size: int = 50,
        q: str = "",
        event_type: str = "",
        significant_only: bool = False,
        order_by: str = "fdr",
    ) -> dict[str, Any]:
        """Paged, filterable event browser for a *historical* project.

        Paging happens in SQLite: real rMATS runs carry 10^5-10^6 events, which
        cannot be shipped to the browser in one response.
        """
        from epitoperank.memory.project_memory import ProjectMemory

        memory = ProjectMemory(settings.paths.memory_db)
        if memory.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        size = max(1, min(int(size), 500))
        page = max(1, int(page))
        filters = {
            "search": q.strip(),
            "event_type": event_type.strip(),
            "significant_only": bool(significant_only),
        }
        total = memory.count_events(project_id, **filters)
        rows = memory.query_events(
            project_id,
            offset=(page - 1) * size,
            limit=size,
            order_by=order_by,
            **filters,
        )
        return {
            "project_id": project_id,
            "total": total,
            "page": page,
            "size": size,
            "pages": max(1, (total + size - 1) // size),
            "events": rows,
            "event_types": memory.event_type_counts(project_id),
        }

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str) -> dict[str, Any]:
        """Delete a project: database rows plus its output folder."""
        from epitoperank.memory.project_memory import ProjectMemory

        memory = ProjectMemory(settings.paths.memory_db)
        if memory.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        removed_rows = memory.delete_project(project_id)
        project_dir = settings.paths.runtime_root / "projects" / project_id
        if project_dir.is_dir():
            shutil.rmtree(project_dir, ignore_errors=True)
        return {"deleted": project_id, "rows": removed_rows}

    @app.post("/api/projects/{project_id}/export")
    def export_project(project_id: str) -> dict[str, Any]:
        """Publish this project's report/figures into its own results folder."""
        from epitoperank.memory.project_memory import ProjectMemory

        memory = ProjectMemory(settings.paths.memory_db)
        project = memory.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        name = project.get("name") if isinstance(project, dict) else ""
        bundle = _export_project_bundle(settings, project_id, str(name or project_id))
        if not bundle:
            raise HTTPException(
                status_code=404,
                detail="这个项目还没有可导出的报告，跑完分析后再试",
            )
        return {"ok": True, "path": bundle}

    @app.post("/api/projects/{project_id}/reveal-bundle")
    def reveal_project_bundle(project_id: str) -> dict[str, Any]:
        """Export (if needed) and open the folder in the system file manager."""
        from epitoperank.memory.project_memory import ProjectMemory

        memory = ProjectMemory(settings.paths.memory_db)
        project = memory.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        name = project.get("name") if isinstance(project, dict) else ""
        bundle = _export_project_bundle(settings, project_id, str(name or project_id))
        if not bundle:
            raise HTTPException(status_code=404, detail="这个项目还没有可导出的报告")
        try:
            if sys.platform == "win32":
                os.startfile(bundle)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", bundle])
            else:
                subprocess.Popen(["xdg-open", bundle])
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"Cannot open folder: {error}") from error
        return {"ok": True, "path": bundle}

    def _bundle_dir_for(project_id: str) -> str:
        from epitoperank.memory.project_memory import ProjectMemory

        memory = ProjectMemory(settings.paths.memory_db)
        project = memory.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        name = project.get("name") if isinstance(project, dict) else ""
        bundle = _export_project_bundle(settings, project_id, str(name or project_id))
        if not bundle:
            raise HTTPException(status_code=404, detail="这个项目还没有可导出的报告")
        return bundle

    @app.post("/api/projects/{project_id}/package")
    def package_project(project_id: str) -> dict[str, Any]:
        """Zip the project's results folder for e-mail, archive or upload."""
        from epitoperank.results_export import package_bundle

        archive = package_bundle(_bundle_dir_for(project_id))
        if archive is None:
            raise HTTPException(status_code=404, detail="打包失败：成果文件夹不存在")
        return {"ok": True, "path": str(archive), "size_mb": round(archive.stat().st_size / 1048576, 2)}

    @app.post("/api/projects/{project_id}/upload")
    def upload_project(project_id: str) -> dict[str, Any]:
        """Push the project's bundle to the configured cloud endpoint."""
        from epitoperank.results_export import (
            cloud_upload_target,
            package_bundle,
            upload_bundle,
        )

        url, _token = cloud_upload_target()
        if not url:
            raise HTTPException(
                status_code=400,
                detail="还没有配置云端地址（环境变量 EPITOPERANK_CLOUD_URL）",
            )
        archive = package_bundle(_bundle_dir_for(project_id))
        if archive is None:
            raise HTTPException(status_code=404, detail="打包失败：成果文件夹不存在")
        result = upload_bundle(archive)
        if not result.get("ok"):
            raise HTTPException(status_code=502, detail=f"上传失败：{result.get('detail')}")
        return {"ok": True, "archive": str(archive), "cloud": result.get("detail", "")}

    @app.post("/api/cloud/upload")
    async def cloud_receive(file: UploadFile = File(...)) -> dict[str, Any]:
        """Receive a results bundle from a desktop client (server-side endpoint)."""
        target_dir = settings.paths.runtime_root / "cloud_receipts"
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "bundle.zip").name
        destination = target_dir / safe_name
        with destination.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                handle.write(chunk)
        return {
            "ok": True,
            "saved": str(destination),
            "size_mb": round(destination.stat().st_size / 1048576, 2),
        }

    @app.post("/api/analyze")
    def analyze(payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query", "")).strip()
        input_dir = str(payload.get("input_dir", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        if not input_dir or not Path(input_dir).exists():
            raise HTTPException(status_code=400, detail=f"input_dir does not exist: {input_dir}")

        run_settings = _with_overrides(settings, payload.get("thresholds"))
        project_name = str(payload.get("project_name") or "").strip()[:120]
        try:
            outcome = run_analysis(query, input_dir, settings=run_settings, project_name=project_name)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        summary = outcome.summary()
        try:
            bundle = _export_project_bundle(
                run_settings, outcome.project_id, project_name, input_dir=input_dir
            )
        except Exception:  # noqa: BLE001 - publishing must never fail a run
            logger.warning("Results bundle failed for %s", outcome.project_id, exc_info=True)
            bundle = ""
        if bundle:
            summary["results_dir"] = bundle
        return JSONResponse(summary)

    def _ingest_input_dir(raw: str) -> Path:
        """Resolve an ingestion directory and keep model exposure local.

        The UI always uploads into the runtime directory; this guard stops a
        remote caller (when the API is exposed) from pointing the model-backed
        profiler at arbitrary files elsewhere on the machine.
        """
        value = str(raw or "").strip()
        if not value:
            raise HTTPException(status_code=400, detail="input_dir is required")
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            raise HTTPException(status_code=400, detail=f"input_dir does not exist: {path}")
        if os.getenv("EPITOPERANK_INGEST_ALLOW_EXTERNAL", "").strip().lower() in {"1", "true", "yes"}:
            return path
        roots = [settings.paths.runtime_root.resolve(), Path.cwd().resolve()]
        if not any(path == root or root in path.parents for root in roots):
            raise HTTPException(
                status_code=400,
                detail="input_dir must be inside the runtime or working directory for ingestion",
            )
        return path

    @app.post("/api/ingest/preview")
    def ingest_preview(payload: dict[str, Any]) -> dict[str, Any]:
        """Profile messy input and propose a reviewed mapping (no files written)."""
        from epitoperank.data.ingestion import preview_ingestion

        directory = _ingest_input_dir(str(payload.get("input_dir", "")))
        try:
            return preview_ingestion(
                directory,
                settings=_fresh_settings(),
                use_llm=bool(payload.get("use_llm", True)),
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:  # noqa: BLE001 - surface a useful 500
            logger.exception("Ingestion preview failed")
            raise HTTPException(status_code=500, detail=f"Ingestion preview failed: {error}") from error

    @app.post("/api/ingest/apply")
    def ingest_apply(payload: dict[str, Any]) -> dict[str, Any]:
        """Convert files with a confirmed mapping into a standardized directory."""
        from epitoperank.data.ingestion import apply_ingestion

        directory = _ingest_input_dir(str(payload.get("input_dir", "")))
        mapping = payload.get("mapping")
        if not isinstance(mapping, dict) or not mapping:
            raise HTTPException(status_code=400, detail="mapping is required")
        try:
            return apply_ingestion(directory, mapping)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"Cannot write standardized data: {error}") from error
        except Exception as error:  # noqa: BLE001 - surface a useful 500
            logger.exception("Ingestion apply failed")
            raise HTTPException(status_code=500, detail=f"Ingestion apply failed: {error}") from error

    @app.post("/api/ingest/groups")
    def ingest_groups(payload: dict[str, Any]) -> dict[str, Any]:
        """Persist confirmed sample groups for an already recognized input."""
        from epitoperank.data.ingestion import apply_native_groups

        directory = _ingest_input_dir(str(payload.get("input_dir", "")))
        groups = payload.get("sample_groups")
        if not isinstance(groups, dict):
            raise HTTPException(status_code=400, detail="sample_groups is required")
        try:
            return apply_native_groups(directory, groups)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    neo_workflows: dict[str, dict] = {}
    neo_workflows_lock = threading.RLock()
    neo_workflows_dir = settings.paths.runtime_root / 'neoantigen_workflows'

    def _neo_session_file(workflow_id: str) -> Path:
        if not re.fullmatch(r'[A-Za-z0-9_-]{32}', workflow_id):
            raise HTTPException(status_code=404, detail='流程不存在')
        return neo_workflows_dir / (workflow_id + '.json')

    def _neo_save(workflow_id: str, session: dict) -> None:
        path = _neo_session_file(workflow_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(session, ensure_ascii=False), encoding='utf-8')
        os.replace(temporary, path)
        neo_workflows[workflow_id] = session

    def _neo_load(workflow_id: str) -> dict:
        path = _neo_session_file(workflow_id)
        if workflow_id not in neo_workflows:
            try:
                neo_workflows[workflow_id] = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                raise HTTPException(status_code=404, detail='流程不存在或无法读取')
        return neo_workflows[workflow_id]

    @app.get('/api/neoantigen/workflow/{workflow_id}')
    def neo_workflow_get(workflow_id: str) -> dict[str, Any]:
        with neo_workflows_lock:
            session = _neo_load(workflow_id)
            return {'workflow_id': workflow_id, **session['state']}

    @app.get('/api/neoantigen/readiness/{project_id}')
    def neo_readiness(project_id: str) -> dict[str, Any]:
        import csv
        from epitoperank.data.loader import load_dataset
        from epitoperank.neoantigen import (CDS_FIELD_LABELS, CDS_FIELDS, discover_cds_tables,
                                           pick_cds_table)
        from epitoperank.splicing.parsers.rmats import RMATS_EVENT_FILES
        project = project_status(project_id, settings)
        if not project:
            raise HTTPException(status_code=404, detail='未找到项目，请先选择项目')
        directory = _ingest_input_dir(str(project['project'].get('source_dir') or ''))
        roots = [directory]
        if directory.name == 'standardized':
            roots.append(_ingest_input_dir(str(directory.parent)))
        try:
            dataset = load_dataset(directory)
            event_ids = {event.event_id for event in dataset.events}
            # Detection is header-based: any table carrying the four CDS columns
            # works, whatever name the customer gave the file.
            discovered = discover_cds_tables(*roots, include_partial=True, event_ids=event_ids)
            candidates = [item for item in discovered if item['valid']]
            partial = [item for item in discovered if not item['valid']]
            chosen = pick_cds_table(candidates)
            details = {}
            for item in candidates:
                stored = _load_cds_mappings(Path(item['path']).parent).get(item['name'], {})
                mapping = stored.get('map') or item['mapping']
                details[item['name']] = {
                    'map': mapping,
                    'source': 'saved' if stored else item['mapping_source'],
                    'confidence': 'high' if stored else item['confidence'],
                    'needs_confirmation': False if stored else item['needs_confirmation'],
                    'header': item['header'],
                    'preview': item['preview'],
                    'row_count': item.get('row_count') or 0,
                }
            return {'project_name': project['project'].get('name') or project_id,
                    'event_count': len(dataset.events),
                    'cds_status': 'available' if candidates else 'missing',
                    'cds_files': [item['name'] for item in candidates],
                    'cds_selected': chosen.name if chosen else None,
                    'cds_choices': [{'name': item['name'], 'columns': item['header']} for item in candidates],
                    'cds_details': details,
                    'cds_needs_confirmation': bool(chosen and details.get(chosen.name, {}).get('needs_confirmation')),
                    'cds_partial': [{'name': item['name'], 'missing': item['missing'],
                                     'reason': item['reason']} for item in partial[:5]],
                    'field_labels': CDS_FIELD_LABELS,
                    'required_fields': list(CDS_FIELDS),
                    'rmats_files': [filename for root in roots for filename in RMATS_EVENT_FILES.values() if (root / filename).is_file()],
                    'note': '仅检查表头与列内容，序列读码框和数据质量须在分析时进一步核实。'}
        except (ValueError, OSError, UnicodeError, csv.Error) as error:
            raise HTTPException(status_code=422, detail=f'无法读取项目数据：{error}') from error

    @app.post('/api/neoantigen/mopepgen')
    def neo_mopepgen(payload: dict[str, Any]) -> dict[str, Any]:
        from epitoperank.mopepgen_docker import execute
        project = project_status(str(payload.get('project_id') or ''), settings)
        if not project:
            raise HTTPException(status_code=404, detail='请先选择有效项目')
        directory = _ingest_input_dir(str(project['project'].get('source_dir') or ''))
        root = _ingest_input_dir(str(directory.parent)) if directory.name == 'standardized' else directory
        def input_file(value: Any) -> Path:
            path = (root / str(value or '')).resolve()
            if root not in path.parents or not path.is_file():
                raise HTTPException(status_code=422, detail='输入文件必须位于当前项目上传目录中')
            return path
        ref_source = payload.get('reference_source')
        version = str(payload.get('reference_version') or '').strip()
        if ref_source not in ('GENCODE', 'ENSEMBL') or not version:
            raise HTTPException(status_code=422, detail='请选择参考来源并填写基因组及注释版本')
        reference = {key: input_file(payload.get(key)) for key in ('genome', 'gtf', 'proteome')}
        if any(path.suffix.lower() == '.gz' for path in reference.values()):
            raise HTTPException(status_code=422, detail='请先解压参考文件，提供未压缩的 FASTA 和 GTF')
        tables = {}
        for key in ('se', 'a3ss', 'a5ss', 'mxe', 'ri'):
            if payload.get(key):
                tables[key] = input_file(payload[key])
        if not tables:
            from epitoperank.splicing.parsers.rmats import RMATS_EVENT_FILES
            tables = {kind.lower(): path for kind, filename in RMATS_EVENT_FILES.items()
                      for path in [root / filename] if path.is_file() and path.resolve().parent == root}
        if not tables:
            raise HTTPException(status_code=422, detail='当前项目未找到原始 rMATS JC 文件；请在高级选项指定文件')
        output = directory / 'mopepgen_results' / secrets.token_hex(12)
        args = ['--genome', str(reference['genome']), '--gtf', str(reference['gtf']),
                '--proteome', str(reference['proteome']), '--reference-source', ref_source,
                '--reference-version', version, '--output', str(output)]
        for key, path in tables.items():
            args.extend(['--' + key, str(path)])
        try:
            code = execute(args)
            manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
        except (OSError, ValueError, SystemExit) as error:
            raise HTTPException(status_code=422, detail=f'moPepGen 无法启动：{error}') from error
        return {'output_dir': str(output), 'exit_code': code, 'manifest': manifest}

    @app.get('/api/neoantigen/mopepgen/file')
    def neo_mopepgen_file(output_dir: str, name: str) -> FileResponse:
        directory = _ingest_input_dir(output_dir)
        if directory.parent.name != 'mopepgen_results' or name not in {'manifest.json', 'events.gvf', 'variant_peptides.fasta', 'step_1.log', 'step_2.log'}:
            raise HTTPException(status_code=400, detail='无效结果文件')
        path = directory / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail='结果文件不存在')
        return FileResponse(path, filename=name)

    @app.post('/api/neoantigen/workflow/start')
    def neo_workflow_start(payload: dict[str, Any]) -> dict[str, Any]:
        from epitoperank.data.loader import load_dataset
        from epitoperank.neoantigen_workflow import start
        project = project_status(str(payload.get('project_id') or ''), settings)
        if not project:
            raise HTTPException(status_code=404, detail='请先选择有效项目')
        directory = _ingest_input_dir(str(project['project'].get('source_dir') or ''))
        evidence = payload.get('evidence') or {}
        if not isinstance(evidence, dict):
            raise HTTPException(status_code=422, detail='evidence 必须为对象')
        try:
            state = start(load_dataset(directory), evidence)
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        workflow_id = secrets.token_urlsafe(24)
        with neo_workflows_lock:
            _neo_save(workflow_id, {'directory': str(directory), 'state': state})
        return {'workflow_id': workflow_id, **state}

    @app.post('/api/neoantigen/workflow/advance')
    def neo_workflow_advance(payload: dict[str, Any]) -> dict[str, Any]:
        from epitoperank.data.loader import load_dataset
        from epitoperank.neoantigen_workflow import advance
        workflow_id = str(payload.get('workflow_id') or '')
        params = payload.get('parameters') or {}
        if not isinstance(params, dict):
            raise HTTPException(status_code=422, detail='parameters 必须为对象')
        with neo_workflows_lock:
            session = _neo_load(workflow_id)
            if payload.get('expected_stage') != session['state']['next_stage']:
                raise HTTPException(status_code=409, detail='阶段已改变，请刷新状态')
            try:
                state = advance(session['state'], load_dataset(session['directory']), params)
            except (ValueError, TypeError, OSError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            _neo_save(workflow_id, {**session, 'state': state})
        return {'workflow_id': workflow_id, **state}

    @app.post("/api/neoantigen/audit")
    def neoantigen_audit(payload: dict[str, Any]) -> dict[str, Any]:
        from epitoperank.data.loader import load_dataset
        from epitoperank.neoantigen_audit import audit, filter_events

        project_id = str(payload.get('project_id') or '').strip()
        if project_id:
            project = project_status(project_id, settings)
            if not project:
                raise HTTPException(status_code=404, detail='项目不存在')
            directory = _ingest_input_dir(str(project['project'].get('source_dir') or ''))
        else:
            directory = _ingest_input_dir(str(payload.get('input_dir') or ''))
        try:
            dataset = load_dataset(directory)
            if payload.get('stage', 0) == 0:
                return audit(dataset, payload.get('evidence') or {})
            if payload.get('stage') == 2:
                if payload.get('audit_confirmed') is not True:
                    raise ValueError('请先完成并确认阶段 0 数据审计')
                return filter_events(dataset, min_support=payload.get('min_support'),
                                     min_samples=payload.get('min_samples'),
                                     support_is_junction_reads=payload.get('support_is_junction_reads', False))
            raise ValueError('目前仅支持阶段 0 审计及阶段 2 事件级过滤')
        except (ValueError, TypeError, OSError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    def _project_input_dirs(project_id: str) -> tuple[Path, list[Path]]:
        project = project_status(project_id, settings)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在，请重新选择项目")
        directory = _ingest_input_dir(str(project['project'].get('source_dir') or ''))
        roots = [directory]
        if directory.name == 'standardized':
            roots.append(_ingest_input_dir(str(directory.parent)))
        return directory, roots

    def _resolve_cds_table(value: Any, roots: list[Path]) -> Path:
        """Map a customer-supplied file name or path onto an existing CDS table."""
        from epitoperank.neoantigen import inspect_cds_table

        raw = str(value or "").strip()
        if not raw:
            raise HTTPException(status_code=422, detail="请先选择编码序列表文件")
        requested = Path(raw).expanduser()
        options = [requested] if requested.is_absolute() else [root / requested for root in roots]
        allowed = [root.resolve() for root in roots]
        for option in options:
            try:
                resolved = option.resolve()
            except OSError:
                continue
            if not resolved.is_file():
                continue
            if not any(resolved.parent == root or root in resolved.parents for root in allowed):
                raise HTTPException(status_code=422, detail="编码序列表必须位于当前项目的数据目录中，请先上传到项目")
            info = inspect_cds_table(resolved)
            if not info['valid']:
                raise HTTPException(status_code=422, detail=f"{resolved.name} 不能作为编码序列表：{info['reason']}")
            return resolved
        raise HTTPException(status_code=404, detail=f"当前项目里没有找到文件「{raw}」，请重新选择或上传")

    def _detect_cds_table(roots: list[Path]) -> Path:
        from epitoperank.neoantigen import discover_cds_tables

        candidates = discover_cds_tables(*roots)
        if not candidates:
            raise HTTPException(status_code=422, detail=(
                "当前项目里还没找到编码序列表。需要一份包含 event_id、reference_cds、altered_cds、"
                "junction_nt 四列的表（TSV/CSV/TXT，文件名不限），上传后即可生成候选肽。"))
        return candidates[0]['path']

    # Customer-confirmed column mappings live next to the table so a manual fix
    # only has to be made once per project.
    def _load_cds_mappings(directory: Path) -> dict[str, Any]:
        path = Path(directory) / CDS_MAPPING_FILE
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_cds_mapping(directory: Path, name: str, mapping: dict[str, str]) -> None:
        data = _load_cds_mappings(directory)
        data[name] = {'map': mapping}
        (Path(directory) / CDS_MAPPING_FILE).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _mapping_for(table: Path, requested: Any, roots: list[Path]) -> dict[str, str] | None:
        """Merge an explicit mapping from the request with one saved earlier."""
        saved = _load_cds_mappings(Path(table).parent).get(Path(table).name, {}).get('map') or {}
        supplied = requested if isinstance(requested, dict) else {}
        merged = {str(key): str(value) for key, value in {**saved, **supplied}.items()
                  if str(value or '').strip()}
        return merged or None

    @app.post("/api/neoantigen/column-map")
    def neo_column_map(payload: dict[str, Any]) -> dict[str, Any]:
        """Persist a human-confirmed column mapping for one CDS table."""
        from epitoperank.neoantigen import CDS_FIELDS, read_table_rows

        directory, roots = _project_input_dirs(str(payload.get("project_id") or "").strip())
        table = _resolve_cds_table(payload.get("file"), roots)
        mapping = payload.get("map") or {}
        if not isinstance(mapping, dict):
            raise HTTPException(status_code=400, detail="列映射格式应为 {字段: 列名}")
        try:
            header, body, _delimiter = read_table_rows(table, limit=5)
        except OSError as error:
            raise HTTPException(status_code=422, detail=f"无法读取 {table.name}：{error}") from error
        cleaned: dict[str, str] = {}
        for field in CDS_FIELDS:
            value = str(mapping.get(field) or "").strip()
            if not value:
                raise HTTPException(status_code=422, detail=f"请为每个字段选择一列（缺少 {field}）")
            if value not in header:
                raise HTTPException(status_code=422, detail=f"表里没有列「{value}」")
            cleaned[field] = value
        if len(set(cleaned.values())) != len(cleaned):
            raise HTTPException(status_code=422, detail="同一个列不能承担两个字段角色，请分别选择")
        # Verify the mapping really produces peptides before we remember it.
        from epitoperank.neoantigen import junction_peptides

        produced = 0
        for row in body:
            cells = {field: (row[header.index(name)] if header.index(name) < len(row) else '').strip()
                     for field, name in cleaned.items()}
            try:
                if junction_peptides(cells['reference_cds'], cells['altered_cds'],
                                     int(cells['junction_nt'])):
                    produced += 1
            except (ValueError, TypeError):
                continue
        _save_cds_mapping(Path(table).parent, table.name, cleaned)
        return {'saved': table.name, 'map': cleaned,
                'verified_rows': produced,
                'warning': None if produced else '这套映射没有为样本行生成任何肽，请核对参考与改变后序列是否填反。'}

    @app.post("/api/neoantigen/cds-upload")
    async def neo_cds_upload(project_id: Annotated[str, Form()], file: Annotated[UploadFile, File()]) -> dict[str, Any]:
        """Store a CDS table chosen from the customer's disk into the project directory."""
        from epitoperank.neoantigen import CDS_TABLE_MAX_BYTES, CDS_TABLE_SUFFIXES, discover_cds_tables, inspect_cds_table

        directory, roots = _project_input_dirs(str(project_id or '').strip())
        name = Path(file.filename or "").name
        if not name:
            raise HTTPException(status_code=400, detail="请选择一个文件")
        if Path(name).suffix.lower() not in CDS_TABLE_SUFFIXES:
            raise HTTPException(status_code=422, detail="编码序列表只支持 TSV、CSV 或 TXT 文本文件（Excel 请另存为 CSV）")
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail=f"{name} 是空文件")
        if len(content) > CDS_TABLE_MAX_BYTES:
            raise HTTPException(status_code=413, detail=f"{name} 超过 {CDS_TABLE_MAX_BYTES // (1024 * 1024)} MB 上限")
        target = directory / name
        target.write_bytes(content)
        info = inspect_cds_table(target)
        if not info['valid']:
            try:
                target.unlink()
            except OSError:
                pass
            raise HTTPException(status_code=422, detail=(
                f"{name} 不能作为编码序列表：{info['reason']}。需要包含 event_id、reference_cds、"
                "altered_cds、junction_nt 四列（列名可用常见别名，如事件ID / 参考序列 / 变异序列 / 连接点）。"))
        discovered = discover_cds_tables(*roots)
        return {'saved': name, 'cds_status': 'available',
                'cds_files': [item['name'] for item in discovered],
                'cds_selected': name, 'columns': info['header']}

    @app.post("/api/neoantigen/run")
    def neoantigen_run(payload: dict[str, Any]) -> dict[str, Any]:
        """Generate auditable junction peptides; optionally query IEDB."""
        from epitoperank.neoantigen import run

        project_id = str(payload.get("project_id") or "").strip()
        requested = payload.get("cds_table")
        if project_id:
            directory, roots = _project_input_dirs(project_id)
        else:
            directory = _ingest_input_dir(str(payload.get("input_dir", "")))
            roots = [directory]
        cds_table = _resolve_cds_table(requested, roots) if str(requested or "").strip() else _detect_cds_table(roots)
        alleles = payload.get("alleles") or []
        if not isinstance(alleles, list):
            raise HTTPException(status_code=400, detail="alleles must be a list")
        output = directory / "neoantigen_results"
        from epitoperank.neoantigen import DEFAULT_MAX_PREDICTIONS

        try:
            max_predictions = int(payload.get("max_predictions") or DEFAULT_MAX_PREDICTIONS)
        except (TypeError, ValueError):
            max_predictions = DEFAULT_MAX_PREDICTIONS
        try:
            result = run(directory, cds_table, output, alleles=alleles,
                         max_predictions=max_predictions,
                         column_map=_mapping_for(cds_table, payload.get("column_map"), roots))
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        result['cds_table_name'] = cds_table.name
        result['cds_table_auto_selected'] = not str(requested or "").strip()
        return result

    @app.get("/api/neoantigen/file")
    def neoantigen_file(input_dir: str, name: str) -> FileResponse:
        directory = _ingest_input_dir(input_dir)
        if name not in {"splice_peptides.tsv", "mhc_i_predictions.tsv", "neoantigen_manifest.json"}:
            raise HTTPException(status_code=400, detail="Unsupported result file")
        path = directory / "neoantigen_results" / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Result file not found")
        return FileResponse(path, filename=name)

    @app.post("/api/neoantigen/reveal")
    def neoantigen_reveal(payload: dict[str, Any]) -> dict[str, Any]:
        """Open results folder in system file manager (desktop only)."""
        directory = _ingest_input_dir(str(payload.get("input_dir", "")))
        results = directory / "neoantigen_results"
        if not results.is_dir():
            raise HTTPException(status_code=404, detail="Result directory not found")
        try:
            if sys.platform == "win32":
                os.startfile(str(results))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(results)])
            else:
                subprocess.Popen(["xdg-open", str(results)])
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"Cannot open results folder: {error}") from error
        return {"ok": True, "path": str(results)}

    # ------------------------------------------------------------------
    # Peptide prediction (MHC-I/II binding, processing, ranking)
    # ------------------------------------------------------------------

    @app.get("/api/peptide/capabilities")
    def peptide_capabilities() -> dict[str, Any]:
        """Report which peptide predictors, models and reference tables exist."""
        from epitoperank.peptide import capabilities

        try:
            return capabilities()
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/peptide/reference")
    def peptide_reference(
        mhc_class: int = 1, search: str = "", limit: int = 500
    ) -> dict[str, Any]:
        """Search the bundled IEDB-derived allele catalogue."""
        from epitoperank.peptide import reference

        if mhc_class not in (1, 2):
            raise HTTPException(status_code=422, detail="mhc_class must be 1 or 2")
        limit = max(1, min(int(limit), 5000))
        try:
            items = reference.load_alleles(mhc_class)
            manifest = reference.manifest()
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        needle = str(search or "").strip().lower()
        if needle:
            items = [item for item in items
                     if needle in str(item.get("allele", "")).lower()]
        return {"total": len(items), "items": items[:limit], "manifest": manifest}

    @app.post("/api/peptide/predict")
    def peptide_predict(payload: dict[str, Any]) -> dict[str, Any]:
        """Predict MHC binding/processing for a small peptide list."""
        from epitoperank.peptide import IedbError, predict_peptides
        from epitoperank.peptide.sequences import normalize_peptide

        raw_peptides = payload.get("peptides")
        raw_alleles = payload.get("alleles")
        if not isinstance(raw_peptides, list) or not raw_peptides:
            raise HTTPException(status_code=422, detail="peptides must be a non-empty list")
        if not isinstance(raw_alleles, list) or not raw_alleles:
            raise HTTPException(status_code=422, detail="alleles must be a non-empty list")
        if len(raw_peptides) > 2000:
            raise HTTPException(status_code=422, detail="单次最多 2000 条肽；更多请分批提交")
        if len(raw_alleles) > 8:
            raise HTTPException(status_code=422, detail="at most 8 alleles per request")
        peptides: list[str] = []
        for value in raw_peptides:
            try:
                peptide = normalize_peptide(str(value))
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            if not 8 <= len(peptide) <= 30:
                raise HTTPException(
                    status_code=422,
                    detail=f"peptide length must be 8-30 aa: {peptide}",
                )
            peptides.append(peptide)
        alleles = [str(item).strip() for item in raw_alleles if str(item).strip()]
        if not alleles:
            raise HTTPException(status_code=422, detail="alleles must be a non-empty list")
        mhc_class = str(payload.get("mhc_class") or "class1")
        predictor = str(payload.get("predictor") or "iedb")
        if mhc_class not in {"class1", "class2", "both"}:
            raise HTTPException(status_code=422, detail="mhc_class must be class1, class2 or both")
        if predictor not in {"iedb", "local", "auto", "none"}:
            raise HTTPException(status_code=422, detail="predictor must be iedb, local, auto or none")
        processing = bool(payload.get("processing", True))
        lookup_epitopes = bool(payload.get("lookup_epitopes", False))

        try:
            if predictor == "none":
                # Offline smoke test: no model is consulted and no network call is made.
                result: dict[str, Any] = {"predictions": [], "errors": [],
                                          "methods": {}}
            else:
                result = predict_peptides(
                    peptides,
                    alleles,
                    mhc_class=mhc_class,
                    predictor=predictor,
                    processing=processing,
                )
        except (ValueError, OSError, IedbError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        epitope_matches: list[dict[str, Any]] = []
        if lookup_epitopes and predictor in {"iedb", "auto"} and result.get("predictions"):
            try:
                from epitoperank.peptide import IedbClient

                found = IedbClient().lookup_epitopes(peptides[:10])
                for peptide, hits in found.items():
                    for hit in hits:
                        epitope_matches.append({"candidate_peptide": peptide, **hit})
            except IedbError as error:
                result.setdefault("errors", []).append(
                    {"stage": "epitope_lookup", "error": str(error)[:500]}
                )

        predictions = result.get("predictions") or []
        return {
            "candidate_count": len(peptides),
            "prediction_count": len(predictions),
            "predictions": predictions,
            "errors": result.get("errors") or [],
            "methods": result.get("methods") or {},
            "epitope_matches": epitope_matches,
        }

    @app.post("/api/peptide/run")
    def peptide_run(payload: dict[str, Any]) -> dict[str, Any]:
        """Generate splice-derived candidates, predict, filter and rank peptides."""
        from epitoperank.peptide import PeptideOptions, run as run_peptides

        project_id = str(payload.get("project_id") or "").strip()
        if project_id:
            project = project_status(project_id, settings)
            if not project:
                raise HTTPException(status_code=404, detail="请先选择有效项目")
            directory = _ingest_input_dir(str(project["project"].get("source_dir") or ""))
            search_dirs = [directory]
            if directory.name == "standardized":
                search_dirs.append(_ingest_input_dir(str(directory.parent)))
        else:
            directory = _ingest_input_dir(str(payload.get("input_dir") or ""))
            search_dirs = [directory]
        roots = [path.resolve() for path in search_dirs]

        def input_file(raw: Any, label: str) -> Path:
            value = str(raw or "").strip()
            if not value:
                raise HTTPException(status_code=422, detail=f"{label} 不能为空")
            candidate = Path(value).expanduser()
            path = (candidate if candidate.is_absolute() else directory / candidate).resolve()
            if not any(path == root or root in path.parents for root in roots):
                raise HTTPException(status_code=400, detail="文件必须位于当前项目上传目录内")
            if not path.is_file():
                raise HTTPException(status_code=400, detail=f"{label} 文件不存在")
            return path

        cds_value = str(payload.get("cds_table") or "").strip()
        peptides_value = str(payload.get("peptides_file") or "").strip()
        if cds_value and peptides_value:
            raise HTTPException(status_code=422, detail="cds_table 与 peptides_file 只能提供一个")
        cds_path: Path | None = None
        peptides_path: Path | None = None
        if cds_value:
            cds_path = input_file(cds_value, "cds_table")
        elif peptides_value:
            peptides_path = input_file(peptides_value, "peptides_file")
        else:
            if not project_id:
                raise HTTPException(status_code=422, detail="需要提供 cds_table 或 peptides_file")
            from epitoperank.neoantigen import discover_cds_tables

            detected = discover_cds_tables(*roots)
            if not detected:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "当前项目里还没找到编码序列表。需要一份包含 event_id、reference_cds、altered_cds、"
                        "junction_nt 四列的表（TSV/CSV/TXT，文件名不限），上传后即可生成候选肽。"
                    ),
                )
            cds_path = detected[0]["path"].resolve()

        raw_fastas = payload.get("self_fastas") or []
        if not isinstance(raw_fastas, list):
            raise HTTPException(status_code=422, detail="self_fastas 必须为路径列表")
        self_fastas = [str(input_file(item, "self_fastas")) for item in raw_fastas]
        raw_alleles = payload.get("alleles") or []
        if not isinstance(raw_alleles, list):
            raise HTTPException(status_code=422, detail="alleles 必须为列表")
        alleles = [str(item).strip() for item in raw_alleles if str(item).strip()]
        mhc_class = str(payload.get("mhc_class") or "both")
        predictor = str(payload.get("predictor") or "iedb")
        if mhc_class not in {"class1", "class2", "both"}:
            raise HTTPException(status_code=422, detail="mhc_class 必须为 class1、class2 或 both")
        if predictor not in {"iedb", "local", "auto", "none"}:
            raise HTTPException(status_code=422, detail="predictor 必须为 iedb、local、auto 或 none")
        try:
            class2_window = int(payload.get("class2_window") or 15)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="class2_window 必须为整数") from None
        options = PeptideOptions(
            alleles=alleles,
            mhc_class=mhc_class,
            predictor=predictor,
            processing=bool(payload.get("processing", True)),
            self_fastas=self_fastas,
            class2_window=class2_window,
            lookup_epitopes=bool(payload.get("lookup_epitopes", False)),
        )
        try:
            return run_peptides(
                output_dir=directory / "peptide_results",
                input_dir=directory if cds_path is not None else None,
                cds_table=cds_path,
                peptides=peptides_path,
                options=options,
            )
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/peptide/file")
    def peptide_file(input_dir: str, name: str) -> FileResponse:
        """Download one whitelisted peptide result file."""
        directory = _ingest_input_dir(input_dir)
        allowed = {
            "splice_peptides.tsv",
            "mhc_predictions.tsv",
            "ranked_candidates.tsv",
            "epitope_matches.tsv",
            "manifest.json",
            "summary.md",
        }
        if name not in allowed:
            raise HTTPException(status_code=400, detail="无效结果文件")
        path = directory / "peptide_results" / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="结果文件不存在")
        return FileResponse(path, filename=name)

    @app.post("/api/upload")
    async def upload(files: list[UploadFile] = File(...)) -> dict[str, Any]:
        """Upload analysis input files into a new staging directory."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Received {len(files)} files in request")
        logger.info(f"Files type: {type(files)}")
        for idx, f in enumerate(files):
            logger.info(f"  File {idx}: {f.filename}, content_type={f.content_type}")
        
        if not files:
            logger.error("No files found in form data")
            raise HTTPException(status_code=400, detail="No files provided")
        
        try:
            staging = Path(tempfile.mkdtemp(prefix="epitoperank_upload_", dir=str(settings.paths.runtime_root)))
            logger.info(f"Created staging directory: {staging}")
            
            uploaded_files = []
            seen_names: set[str] = set()
            for idx, upload in enumerate(files):
                if not upload.filename:
                    logger.warning(f"File {idx} has no filename, skipping")
                    continue
                    
                filename = Path(upload.filename).name
                if filename.lower() in seen_names:
                    raise HTTPException(status_code=422, detail=f"Duplicate uploaded filename: {filename}")
                seen_names.add(filename.lower())
                destination = staging / filename
                logger.info(f"Saving file {idx+1}/{len(files)}: {upload.filename} ({upload.content_type}) -> {destination}")
                
                with destination.open("wb") as handle:
                    size = 0
                    while chunk := await upload.read(1024 * 1024):
                        handle.write(chunk)
                        size += len(chunk)
                    logger.info(f"Saved {size} bytes to {destination}")
                
                uploaded_files.append(upload.filename)
            
            logger.info(f"Upload complete: {len(uploaded_files)} files saved to {staging}")
            return {"upload_dir": str(staging), "files": uploaded_files}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e
    
    # Debug endpoint to test file upload
    @app.post("/api/upload-debug")
    async def upload_debug(request: Request):
        """Debug endpoint to inspect incoming request."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(
            "upload_debug_request",
            extra={
                "event": "upload_debug_request",
                "method": request.method,
                "content_type": request.headers.get("content-type", ""),
            },
        )
        
        try:
            form = await request.form()
            logger.info(f"Form keys: {list(form.keys())}")
            for key, value in form.multi_items():
                logger.info(f"  {key}: {type(value).__name__} - {getattr(value, 'filename', 'N/A')}")
            return {"form_keys": list(form.keys()), "success": True}
        except Exception as e:
            logger.error(f"Form parsing failed: {e}", exc_info=True)
            return {"error": str(e)}

    @app.get("/api/report/{project_id}")
    def report(project_id: str, format: str = "html") -> Any:
        payload = project_status(project_id, settings)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        extension = "pdf" if format.lower() == "pdf" else "html"
        media = "application/pdf" if extension == "pdf" else "text/html"
        # 1) the stored artifact, 2) the conventional location inside the
        # project folder — the second one survives a runtime-root migration
        # even when the database still carries an old absolute path.
        candidates: list[Path] = [
            Path(artifact["path"])
            for artifact in payload["artifacts"]
            if artifact["kind"] == f"report:{extension}"
        ]
        candidates.append(settings.paths.runtime_root / "projects" / project_id / f"report.{extension}")
        for candidate in candidates:
            if candidate.is_file():
                return FileResponse(candidate, media_type=media)
        raise HTTPException(status_code=404, detail=f"No {extension} report for project {project_id}")

    # ==================== MCP Integration Endpoints ====================

    @app.get("/api/mcp/servers")
    async def mcp_servers(refresh: bool = False) -> dict[str, Any]:
        """List configured MCP servers, connection state and tool schemas."""
        from epitoperank.mcp import get_mcp_client

        client = get_mcp_client()
        result: dict[str, Any] = {}

        for server_name, config in client.servers.items():
            if not config.enabled:
                result[server_name] = {
                    "status": "disabled",
                    "transport": config.transport,
                    "builtin": config.builtin,
                    "tools": [],
                }
                continue
            try:
                connected = (
                    await client.refresh(server_name)
                    if refresh
                    else await client.connect(server_name)
                )
                if connected:
                    tools = await client.list_tools(server_name)
                    result[server_name] = {
                        "status": "connected",
                        "transport": config.transport,
                        "via": client._connected_via.get(server_name),
                        "builtin": config.builtin,
                        "url": config.url,
                        "tools": [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.input_schema or {},
                            }
                            for tool in tools
                        ],
                    }
                else:
                    result[server_name] = {
                        "status": "disconnected",
                        "transport": config.transport,
                        "builtin": config.builtin,
                        "url": config.url,
                        "tools": [],
                    }
            except Exception as error:  # noqa: BLE001 - one bad server must not hide others
                result[server_name] = {
                    "status": "error",
                    "transport": config.transport,
                    "builtin": config.builtin,
                    "url": config.url,
                    "error": str(error),
                    "tools": [],
                }

        return {
            "servers": result,
            "config_path": str(client.config_path),
            "builtin_server": "epitoperank-builtin",
        }

    @app.post("/api/mcp/call")
    async def mcp_call_tool(payload: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool on a connected server."""
        from epitoperank.mcp import get_mcp_client

        server_name = str(payload.get("server_name", "")).strip()
        tool_name = str(payload.get("tool_name", "")).strip()
        arguments = payload.get("arguments", {})

        if not server_name or not tool_name:
            raise HTTPException(status_code=400, detail="server_name and tool_name are required")
        if arguments in (None, ""):
            arguments = {}
        if not isinstance(arguments, dict):
            raise HTTPException(status_code=400, detail="arguments must be a JSON object")

        client = get_mcp_client()
        if server_name not in client.servers:
            raise HTTPException(status_code=404, detail=f"unknown MCP server: {server_name}")
        result = await client.call_tool(server_name, tool_name, arguments)

        if "error" in result:
            return {"success": False, "error": result["error"], "raw": result.get("result")}

        return {"success": True, "result": result, "server": server_name, "tool": tool_name}

    @app.post("/api/mcp/agent")
    async def mcp_agent(payload: dict[str, Any]) -> dict[str, Any]:
        """Let the model pick one MCP tool for a natural-language request.

        The model only proposes ``{server, tool, arguments}``; validation and
        execution stay local. Without a model endpoint a deterministic router
        mirrors the same contract, so the demo never dead-ends.
        """
        import asyncio

        question = str(payload.get("question", "")).strip()
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        project_hint = str(payload.get("project_id", "")).strip()

        from epitoperank.mcp import get_mcp_client

        client = get_mcp_client()
        catalog: list[dict[str, Any]] = []
        for server_name, config in client.servers.items():
            if not config.enabled or not await client.connect(server_name):
                continue
            for tool in await client.list_tools(server_name):
                catalog.append(
                    {
                        "server": server_name,
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema or {},
                    }
                )
        if not catalog:
            raise HTTPException(status_code=503, detail="no MCP tools are available")

        project_ids = [
            str(item.get("project_id"))
            for item in list_projects(settings)[:10]
            if item.get("project_id")
        ]
        if project_hint not in project_ids:
            project_hint = ""

        def sanitise(candidate: Any) -> dict[str, Any] | None:
            if not isinstance(candidate, dict):
                return None
            server = str(candidate.get("server", "")).strip()
            tool_name = str(candidate.get("tool", "")).strip()
            arguments = candidate.get("arguments") or {}
            if not tool_name or not isinstance(arguments, dict):
                return None
            entry = next(
                (
                    item
                    for item in catalog
                    if item["server"] == server and item["name"] == tool_name
                ),
                None,
            )
            if entry is None:
                matches = [item for item in catalog if item["name"] == tool_name]
                if len(matches) != 1:
                    return None
                entry = matches[0]
                server = entry["server"]
            schema = entry.get("input_schema") or {}
            allowed = set((schema.get("properties") or {}).keys())
            arguments = {key: value for key, value in arguments.items() if key in allowed}
            if "project_id" in allowed:
                supplied = str(arguments.get("project_id", "")).strip()
                if supplied not in project_ids:
                    arguments["project_id"] = project_hint or (
                        project_ids[0] if project_ids else ""
                    )
                if not arguments["project_id"]:
                    arguments.pop("project_id", None)
            missing = set(schema.get("required") or []) - set(arguments)
            if missing:
                return None
            return {
                "server": server,
                "tool": tool_name,
                "arguments": arguments,
                "reason": str(candidate.get("reason", "")).strip()[:300],
            }

        def rule_plan() -> dict[str, Any]:
            def entry_for(name: str) -> dict[str, Any] | None:
                return next((item for item in catalog if item["name"] == name), None)

            project_id = project_hint or (project_ids[0] if project_ids else "")
            type_match = re.search(
                r"(?<![A-Za-z0-9])(SE|MXE|A5SS|A3SS|RI)(?![A-Za-z0-9])",
                question.upper(),
            )
            if type_match and entry_for("explain_event_type"):
                return {
                    "server": entry_for("explain_event_type")["server"],
                    "tool": "explain_event_type",
                    "arguments": {"event_type": type_match.group(1)},
                    "reason": "识别到剪接事件类型关键词",
                }
            numbers = re.findall(
                r"(?<![\w.])(0(?:\.\d+)?|1(?:\.0+)?)(?![\w.])", question
            )
            if len(numbers) >= 2 and entry_for("compute_delta_psi"):
                return {
                    "server": entry_for("compute_delta_psi")["server"],
                    "tool": "compute_delta_psi",
                    "arguments": {
                        "group1_psi": float(numbers[0]),
                        "group2_psi": float(numbers[1]),
                    },
                    "reason": "识别到两个 PSI 数值，计算 ΔPSI",
                }
            gene_match = re.search(
                r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,9})(?![A-Za-z0-9])", question
            )
            excluded = {
                "PSI", "FDR", "MCP", "RNA", "DNA", "CDNA", "PCR", "AI",
                "SE", "MXE", "RI", "A5SS", "A3SS",
            }
            if (
                gene_match
                and gene_match.group(1) not in excluded
                and entry_for("search_events")
                and project_id
            ):
                return {
                    "server": entry_for("search_events")["server"],
                    "tool": "search_events",
                    "arguments": {
                        "project_id": project_id,
                        "gene": gene_match.group(1),
                        "limit": 10,
                    },
                    "reason": "识别到基因符号，检索该基因的剪接事件",
                }
            if (
                "项目" in question
                and any(word in question for word in ("列表", "哪些", "多少"))
                and entry_for("list_projects")
            ):
                return {
                    "server": entry_for("list_projects")["server"],
                    "tool": "list_projects",
                    "arguments": {},
                    "reason": "询问项目列表",
                }
            if entry_for("project_summary") and project_id:
                return {
                    "server": entry_for("project_summary")["server"],
                    "tool": "project_summary",
                    "arguments": {"project_id": project_id},
                    "reason": "默认读取当前项目摘要",
                }
            if entry_for("list_projects"):
                return {
                    "server": entry_for("list_projects")["server"],
                    "tool": "list_projects",
                    "arguments": {},
                    "reason": "未指定项目，先列出可用项目",
                }
            first = catalog[0]
            return {
                "server": first["server"],
                "tool": first["name"],
                "arguments": {},
                "reason": "默认使用首个可用工具",
            }

        plan: dict[str, Any] | None = None
        source = "rule"
        llm_errors: list[Any] = []
        try:
            from epitoperank.llm.enrich import build_enhancer

            enhancer = build_enhancer(_fresh_settings())
            if enhancer.enabled and enhancer.has("plan"):
                system = (
                    "You route a user's request to exactly one MCP tool. "
                    "Return JSON only with keys: server, tool, arguments, reason. "
                    "Use only the provided servers/tools and their schema properties. "
                    "Never invent project IDs; pick one from projects if needed. "
                    "Prefer search_events for gene-level splicing questions, "
                    "project_summary for whole-project questions, and "
                    "explain_event_type for terminology questions."
                )
                user = json.dumps(
                    {
                        "question": question,
                        "current_project": project_hint or None,
                        "projects": project_ids,
                        "tools": [
                            {
                                "server": item["server"],
                                "tool": item["name"],
                                "description": item["description"],
                                "input_schema": item["input_schema"],
                            }
                            for item in catalog
                        ],
                    },
                    ensure_ascii=False,
                )
                candidate = await asyncio.to_thread(
                    enhancer.json,
                    system=system,
                    user=user,
                    feature="plan",
                    max_tokens=600,
                    timeout=40,
                )
                plan = sanitise(candidate)
                if plan is not None:
                    source = "llm"
                llm_errors = enhancer.errors[-3:]
        except Exception as error:  # noqa: BLE001 - fall back to deterministic routing
            llm_errors = [{"error": str(error)}]

        if plan is None:
            plan = rule_plan()

        started = time.perf_counter()
        result = await client.call_tool(plan["server"], plan["tool"], plan["arguments"])
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "success": "error" not in result,
            "error": result.get("error"),
            "source": source,
            "plan": plan,
            "result": result,
            "elapsed_ms": elapsed_ms,
            "llm_errors": llm_errors,
        }

    # ==================== Skills Endpoints ====================

    @app.get("/api/skills/list")
    def skills_list() -> dict[str, Any]:
        """List all available splicing-specific skills."""
        from epitoperank.skills import (
            GeneAnnotationSkill,
            LiteratureSearchSkill,
            PathwayEnrichmentSkill,
            SpliceInterpretationSkill,
        )

        skills = [
            GeneAnnotationSkill(),
            LiteratureSearchSkill(),
            PathwayEnrichmentSkill(),
            SpliceInterpretationSkill(),
        ]

        return {
            "skills": [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "input_schema": skill.input_schema,
                }
                for skill in skills
            ]
        }

    @app.post("/api/skills/execute")
    async def skills_execute(payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a splicing-specific skill.

        Expected payload:
        {
            "skill_name": "gene_annotation",
            "parameters": {
                "gene_symbol": "BRCA1",
                "include_splicing": true
            }
        }
        """
        skill_name = payload.get("skill_name")
        parameters = payload.get("parameters", {})

        if not skill_name:
            raise HTTPException(status_code=400, detail="skill_name is required")

        # Import and instantiate the requested skill
        skill_map = {
            "gene_annotation": "GeneAnnotationSkill",
            "literature_search": "LiteratureSearchSkill",
            "pathway_enrichment": "PathwayEnrichmentSkill",
            "splice_interpretation": "SpliceInterpretationSkill",
        }

        skill_class_name = skill_map.get(skill_name)
        if not skill_class_name:
            raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_name}")

        # Dynamic import to avoid circular dependencies
        import importlib

        module = importlib.import_module("epitoperank.skills")
        skill_class = getattr(module, skill_class_name)
        skill = skill_class()

        # Validate input
        is_valid, error_msg = skill.validate_input(**parameters)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Execute the skill
        result = await skill.execute(**parameters)

        return result.to_dict()

    @app.get("/api/figure/{project_id}/{figure_name}")
    def figure(project_id: str, figure_name: str) -> Any:
        safe_name = Path(figure_name).stem
        for extension in (".png", ".svg"):
            candidate = settings.paths.runtime_root / "projects" / project_id / "figures" / f"{safe_name}{extension}"
            if candidate.is_file():
                return FileResponse(candidate)
        payload = project_status(project_id, settings)
        if payload is not None:
            for artifact in payload["artifacts"]:
                if artifact["kind"] == f"figure:{safe_name}" and Path(artifact["path"]).is_file():
                    return FileResponse(artifact["path"])
            if safe_name in extra_figures.ON_DEMAND_FIGURES:
                target_dir = settings.paths.runtime_root / "projects" / project_id / "figures"
                try:
                    generated = _build_on_demand_figure(safe_name, payload, target_dir)
                    if generated is not None and generated.is_file():
                        return FileResponse(generated)
                except Exception as exc:  # noqa: BLE001 - never crash the endpoint
                    logger.warning("on-demand figure %s failed: %s", safe_name, exc)
        raise HTTPException(status_code=404, detail=f"Figure {figure_name} not found")

    return app


def _build_on_demand_figure(name: str, payload: dict[str, Any], target_dir: Path) -> Path | None:
    """Generate a lazy figure from persisted project state."""
    candidates = payload.get("candidates") or []
    samples = payload.get("samples") or []
    if name == "dpsi_waterfall":
        return extra_figures.plot_dpsi_waterfall(candidates, target_dir)
    if name == "dpsi_ecdf":
        return extra_figures.plot_dpsi_ecdf(candidates, target_dir)
    if name == "fdr_scree":
        return extra_figures.plot_fdr_scree(candidates, target_dir)
    if name == "event_significance":
        return extra_figures.plot_event_significance(candidates, target_dir)
    if name == "score_components":
        return extra_figures.plot_score_components(candidates, target_dir)
    if name == "sample_composition":
        return extra_figures.plot_sample_composition(samples, target_dir)
    if name == "event_schematic":
        return extra_figures.plot_event_schematic(target_dir)
    return None


app = create_app()

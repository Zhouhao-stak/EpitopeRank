"""Analysis Memory: durable project state in SQLite.

Persists everything the prompt requires an analysis to remember:

* input data fingerprint
* analysis plan
* generated code / parameters
* results (events, candidates, enrichment, figures)
* interpretation and report artifacts
* workflow logs (agent-by-agent trace)
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _wal_enabled() -> bool:
    """True when ``SPLICEGAIP_SQLITE_WAL`` asks for write-ahead logging.

    Multi-process serving (``serve_ui.py --workers N``) needs WAL so readers
    are not blocked by a running analysis write. It stays opt-in because WAL
    corrupts on some network filesystems.
    """
    return os.environ.get("SPLICEGAIP_SQLITE_WAL", "").strip().lower() in _TRUE_VALUES

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    source_dir TEXT,
    source_format TEXT,
    species TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS samples (
    project_id TEXT NOT NULL,
    sample_id TEXT NOT NULL,
    group_name TEXT NOT NULL,
    condition TEXT,
    tissue TEXT,
    batch TEXT,
    PRIMARY KEY (project_id, sample_id)
);

CREATE TABLE IF NOT EXISTS events (
    project_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    gene_id TEXT,
    gene_symbol TEXT,
    event_type TEXT,
    chromosome TEXT,
    strand TEXT,
    genomic_coordinates TEXT,
    source_tool TEXT,
    mean_psi_group1 REAL,
    mean_psi_group2 REAL,
    delta_psi REAL,
    p_value REAL,
    fdr REAL,
    inclusion_reads INTEGER,
    exclusion_reads INTEGER,
    total_support_reads INTEGER,
    psi_json TEXT,
    significant INTEGER,
    PRIMARY KEY (project_id, event_id)
);

CREATE TABLE IF NOT EXISTS candidates (
    project_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    gene_id TEXT,
    gene_symbol TEXT,
    event_type TEXT,
    delta_psi REAL,
    fdr REAL,
    score REAL,
    components_json TEXT,
    evidence_json TEXT,
    PRIMARY KEY (project_id, rank)
);

CREATE TABLE IF NOT EXISTS enrichment_terms (
    project_id TEXT NOT NULL,
    ontology TEXT NOT NULL,
    term TEXT NOT NULL,
    gene_count INTEGER,
    background_count INTEGER,
    fold_enrichment REAL,
    p_value REAL,
    fdr REAL,
    genes_json TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    project_id TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interpretations (
    project_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- History browsing filters and counts per project; without these a paged
-- query over a 1.6M-event database does a full table scan every time.
CREATE INDEX IF NOT EXISTS idx_events_project ON events (project_id);
CREATE INDEX IF NOT EXISTS idx_events_project_significant ON events (project_id, significant);
CREATE INDEX IF NOT EXISTS idx_events_project_fdr ON events (project_id, fdr);
CREATE INDEX IF NOT EXISTS idx_events_gene ON events (project_id, gene_symbol);
CREATE INDEX IF NOT EXISTS idx_candidates_project ON candidates (project_id);
CREATE INDEX IF NOT EXISTS idx_samples_project ON samples (project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts (project_id);
CREATE INDEX IF NOT EXISTS idx_logs_project ON workflow_logs (project_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_project ON enrichment_terms (project_id);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProjectMemory:
    """SQLite-backed analysis memory (thread-safe)."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            # WAL lets several uvicorn workers read while one of them writes.
            # Opt-in because WAL is unsafe on NFS/SMB, where most HPC home
            # directories live; the default rollback journal is the safe choice
            # for a single process on a network mount.
            if _wal_enabled():
                try:
                    connection.execute("PRAGMA journal_mode=WAL")
                except sqlite3.DatabaseError:
                    pass  # network filesystem refused WAL: keep the default

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        # ``synchronous`` is per-connection (journal_mode is not), so the WAL
        # fast path has to be re-applied on every connection.
        if _wal_enabled():
            connection.execute("PRAGMA synchronous=NORMAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    # -- projects ---------------------------------------------------------
    def create_project(
        self,
        project_id: str,
        name: str,
        query: str,
        source_dir: str = "",
        source_format: str = "",
        species: str = "",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO projects "
                "(project_id, name, query, source_dir, source_format, species, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_id, name, query, source_dir, source_format, species, _utc_now()),
            )

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM projects ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    # -- samples ----------------------------------------------------------
    def save_samples(self, project_id: str, samples: Sequence[Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM samples WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT INTO samples (project_id, sample_id, group_name, condition, tissue, batch) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        sample.sample_id,
                        sample.group,
                        sample.condition,
                        sample.tissue,
                        sample.batch,
                    )
                    for sample in samples
                ],
            )

    def load_samples(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM samples WHERE project_id = ? ORDER BY sample_id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- events -----------------------------------------------------------
    def save_events(
        self,
        project_id: str,
        events: Sequence[Any],
        significant_ids: set[str] | None = None,
    ) -> None:
        significant_ids = significant_ids or set()
        with self._connect() as connection:
            connection.execute("DELETE FROM events WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT OR REPLACE INTO events (project_id, event_id, gene_id, gene_symbol, "
                "event_type, chromosome, strand, genomic_coordinates, source_tool, "
                "mean_psi_group1, mean_psi_group2, delta_psi, p_value, fdr, inclusion_reads, "
                "exclusion_reads, total_support_reads, psi_json, significant) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        event.event_id,
                        event.gene_id,
                        event.gene_symbol,
                        event.event_type,
                        event.chromosome,
                        event.strand,
                        event.genomic_coordinates,
                        event.source_tool,
                        event.mean_psi_group1,
                        event.mean_psi_group2,
                        event.delta_psi,
                        event.p_value,
                        event.fdr,
                        event.inclusion_reads,
                        event.exclusion_reads,
                        event.total_support_reads,
                        json.dumps(event.psi_by_sample),
                        1 if event.event_id in significant_ids else 0,
                    )
                    for event in events
                ],
            )

    def load_events(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE project_id = ? ORDER BY event_id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- paged browsing (history view) ------------------------------------
    def _event_filter(
        self,
        project_id: str,
        *,
        search: str = "",
        event_type: str = "",
        significant_only: bool = False,
        fdr_max: float | None = None,
        min_abs_delta: float | None = None,
    ) -> tuple[str, list[Any]]:
        clauses = ["project_id = ?"]
        params: list[Any] = [project_id]
        if search:
            clauses.append("(LOWER(COALESCE(gene_symbol, '')) LIKE ? OR LOWER(COALESCE(gene_id, '')) LIKE ? OR LOWER(event_id) LIKE ?)")
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern])
        if event_type:
            clauses.append("UPPER(COALESCE(event_type, '')) = ?")
            params.append(event_type.upper())
        if significant_only:
            clauses.append("significant = 1")
        if fdr_max is not None:
            clauses.append("fdr IS NOT NULL AND fdr < ?")
            params.append(float(fdr_max))
        if min_abs_delta is not None:
            clauses.append("delta_psi IS NOT NULL AND ABS(delta_psi) > ?")
            params.append(float(min_abs_delta))
        return " AND ".join(clauses), params

    def count_events(self, project_id: str, **filters: Any) -> int:
        where, params = self._event_filter(project_id, **filters)
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) FROM events WHERE {where}", params
            ).fetchone()
        return int(row[0]) if row else 0

    def query_events(
        self,
        project_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        order_by: str = "fdr",
        **filters: Any,
    ) -> list[dict[str, Any]]:
        """Return a page of events, newest/highest-ranked first.

        ``order_by`` accepts ``fdr`` (default), ``delta_psi`` or ``gene``.
        """
        order = {
            "fdr": "fdr IS NULL, fdr ASC, ABS(delta_psi) DESC",
            "delta_psi": "delta_psi IS NULL, ABS(delta_psi) DESC",
            "gene": "COALESCE(gene_symbol, gene_id, '') ASC, event_id ASC",
        }.get(order_by, "fdr IS NULL, fdr ASC, ABS(delta_psi) DESC")
        where, params = self._event_filter(project_id, **filters)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_id, gene_id, gene_symbol, event_type, chromosome, strand, "
                "genomic_coordinates, source_tool, mean_psi_group1, mean_psi_group2, "
                "delta_psi, p_value, fdr, inclusion_reads, exclusion_reads, "
                "total_support_reads, significant "
                f"FROM events WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
                params + [int(limit), int(offset)],
            ).fetchall()
        return [dict(row) for row in rows]

    def event_type_counts(self, project_id: str) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT COALESCE(event_type, 'NA') AS kind, COUNT(*) FROM events "
                "WHERE project_id = ? GROUP BY kind ORDER BY COUNT(*) DESC",
                (project_id,),
            ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def list_projects_with_stats(self) -> list[dict[str, Any]]:
        """Projects plus the counters the history panel needs."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT p.*, "
                "(SELECT COUNT(*) FROM events e WHERE e.project_id = p.project_id) AS event_count, "
                "(SELECT COUNT(*) FROM events e WHERE e.project_id = p.project_id AND e.significant = 1) AS significant_count, "
                "(SELECT COUNT(*) FROM candidates c WHERE c.project_id = p.project_id) AS candidate_count, "
                "(SELECT COUNT(*) FROM samples s WHERE s.project_id = p.project_id) AS sample_count "
                "FROM projects p ORDER BY p.created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_project(self, project_id: str) -> int:
        """Remove every row belonging to ``project_id``; returns rows deleted."""
        tables = (
            "samples",
            "events",
            "candidates",
            "enrichment_terms",
            "artifacts",
            "workflow_logs",
            "plans",
            "interpretations",
            "agent_episodes",
            "projects",
        )
        deleted = 0
        with self._connect() as connection:
            existing = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            for table in tables:
                if table not in existing:
                    continue
                cursor = connection.execute(
                    f"DELETE FROM {table} WHERE project_id = ?", (project_id,)
                )
                deleted += max(cursor.rowcount, 0)
        return deleted

    # -- candidates -------------------------------------------------------
    def save_candidates(self, project_id: str, candidates: Sequence[Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM candidates WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT INTO candidates (project_id, rank, event_id, gene_id, gene_symbol, "
                "event_type, delta_psi, fdr, score, components_json, evidence_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        rank,
                        candidate.event_id,
                        candidate.gene_id,
                        candidate.gene_symbol,
                        candidate.event_type,
                        candidate.delta_psi,
                        candidate.fdr,
                        candidate.score,
                        json.dumps(
                            {
                                "significance": candidate.significance_component,
                                "effect": candidate.effect_component,
                                "biology": candidate.biology_component,
                                "literature": candidate.literature_component,
                            }
                        ),
                        json.dumps(list(candidate.evidence)),
                    )
                    for rank, candidate in enumerate(candidates, start=1)
                ],
            )

    def load_candidates(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM candidates WHERE project_id = ? ORDER BY rank", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- enrichment -------------------------------------------------------
    def save_enrichment(self, project_id: str, results: Sequence[Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM enrichment_terms WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT INTO enrichment_terms (project_id, ontology, term, gene_count, "
                "background_count, fold_enrichment, p_value, fdr, genes_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        result.ontology,
                        result.term,
                        result.gene_count,
                        result.background_count,
                        result.fold_enrichment,
                        result.p_value,
                        result.fdr,
                        json.dumps(list(result.genes)),
                    )
                    for result in results
                ],
            )

    def load_enrichment(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM enrichment_terms WHERE project_id = ? ORDER BY fdr", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- artifacts / plans / interpretations / logs -----------------------
    def save_artifact(self, project_id: str, kind: str, path: str | Path) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts (project_id, kind, path, created_at) VALUES (?, ?, ?, ?)",
                (project_id, kind, str(path), _utc_now()),
            )

    def load_artifacts(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def save_plan(self, project_id: str, plan: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM plans WHERE project_id = ?", (project_id,))
            connection.execute(
                "INSERT INTO plans (project_id, plan_json, created_at) VALUES (?, ?, ?)",
                (project_id, json.dumps(plan), _utc_now()),
            )

    def load_plan(self, project_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT plan_json FROM plans WHERE project_id = ?", (project_id,)
            ).fetchone()
        return json.loads(row["plan_json"]) if row else None

    def save_interpretation(self, project_id: str, agent: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO interpretations (project_id, agent, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (project_id, agent, content, _utc_now()),
            )

    def load_interpretations(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                # ``interpretations`` has no surrogate id column: order by the
                # implicit rowid so insertion order is preserved.
                "SELECT * FROM interpretations WHERE project_id = ? ORDER BY rowid", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def log(
        self,
        project_id: str,
        agent: str,
        action: str,
        status: str = "ok",
        detail: str = "",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO workflow_logs (project_id, agent, action, status, detail, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, agent, action, status, detail[:4000], _utc_now()),
            )

    def load_logs(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_logs WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

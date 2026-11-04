"""Standard MCP stdio server exposing EpitopeRank project and peptide tools.

Run with ``python -m epitoperank.mcp.splice_server``. It speaks the official
Model Context Protocol over stdin/stdout, so any MCP-compatible client can
list and call these tools without knowing anything about EpitopeRank.

The peptide tools import ``epitoperank.peptide`` lazily, so this module stays
importable when the optional prediction dependencies (or the network) are
unavailable.
"""

from __future__ import annotations

from epitoperank.mcp.demo_tools import (
    EVENT_TYPE_GLOSSARY,
    compute_delta_psi as _compute_delta_psi,
    explain_event_type as _explain_event_type,
    list_projects as _list_projects,
    project_summary as _project_summary,
    search_events as _search_events,
)

try:  # mcp >= 2 renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as _ServerClass
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _ServerClass  # type: ignore[assignment]


server = _ServerClass(
    "epitoperank-tools",
    instructions=(
        "Tools for inspecting EpitopeRank alternative-splicing projects (project "
        "summaries, candidate events, event-type definitions, delta-PSI maths) and "
        "for peptide prediction (offline physicochemical features, IEDB MHC-I/II "
        "binding and processing prediction, and known-epitope lookup). Binding "
        "prediction is not antigen presentation or immunogenicity."
    ),
)

#: Per-call caps keep a single MCP request bounded (and IEDB polite).
_MAX_PEPTIDES_PROPERTIES = 50
_MAX_PEPTIDES_PREDICT = 20
_MAX_ALLELES_PREDICT = 4
_MAX_PEPTIDES_LOOKUP = 10


@server.tool()
def list_projects() -> dict:
    """List analyzed EpitopeRank projects with their project_id."""
    return _list_projects()


@server.tool()
def project_summary(project_id: str) -> dict:
    """Summarize one project: samples, events, significant hits, top candidates."""
    return _project_summary(project_id)


@server.tool()
def search_events(
    project_id: str,
    gene: str = "",
    event_type: str = "",
    fdr_max: float = 0.05,
    min_abs_dpsi: float = 0.1,
    limit: int = 20,
) -> dict:
    """Search splicing events by gene, type, FDR and absolute delta PSI."""
    return _search_events(
        project_id=project_id,
        gene=gene,
        event_type=event_type,
        fdr_max=fdr_max,
        min_abs_dpsi=min_abs_dpsi,
        limit=limit,
    )


@server.tool()
def explain_event_type(event_type: str = "") -> dict:
    """Explain SE, MXE, A5SS, A3SS and RI event types (empty returns all)."""
    if not event_type.strip():
        return {"event_types": EVENT_TYPE_GLOSSARY}
    return _explain_event_type(event_type)


@server.tool()
def compute_delta_psi(group1_psi: float, group2_psi: float) -> dict:
    """Compute delta PSI = group2 - group1 and interpret the direction."""
    return _compute_delta_psi(group1_psi, group2_psi)


@server.tool()
def peptide_capabilities() -> dict:
    """Report peptide predictors, IEDB method keys, reference tables and limits."""
    from epitoperank.peptide import capabilities

    return capabilities()


@server.tool()
def peptide_properties(peptides: list[str]) -> dict:
    """Compute offline physicochemical features for up to 50 peptides.

    Returns molecular weight, pI, net charge at pH 7, GRAVY, aromaticity,
    aliphatic index, hydrophobic fraction, Shannon entropy, low-complexity
    flag and the P2/PΩ anchor residues. These are descriptive features, not a
    binding or immunogenicity prediction.
    """
    from epitoperank.peptide.properties import describe_many

    if not isinstance(peptides, list) or not peptides:
        return {"error": "peptides must be a non-empty list"}
    if len(peptides) > _MAX_PEPTIDES_PROPERTIES:
        return {"error": f"at most {_MAX_PEPTIDES_PROPERTIES} peptides per call"}
    try:
        return {"peptides": describe_many(peptides)}
    except ValueError as error:
        return {"error": str(error)}


@server.tool()
def predict_mhc_binding(
    peptides: list[str],
    alleles: list[str],
    mhc_class: str = "class1",
    processing: bool = False,
) -> dict:
    """Predict MHC-I/II binding (IEDB) for up to 20 peptides and 4 alleles.

    ``mhc_class`` is class1, class2 or both; ``processing=True`` also requests
    the IEDB proteasome/TAP processing score. Requires network access to the
    IEDB Analysis Resource. Binding prediction is not presentation or
    immunogenicity.
    """
    from epitoperank.peptide import predict_peptides

    if not isinstance(peptides, list) or not peptides:
        return {"error": "peptides must be a non-empty list"}
    if not isinstance(alleles, list) or not alleles:
        return {"error": "alleles must be a non-empty list"}
    if len(peptides) > _MAX_PEPTIDES_PREDICT:
        return {"error": f"at most {_MAX_PEPTIDES_PREDICT} peptides per call"}
    if len(alleles) > _MAX_ALLELES_PREDICT:
        return {"error": f"at most {_MAX_ALLELES_PREDICT} alleles per call"}
    if mhc_class not in {"class1", "class2", "both"}:
        return {"error": "mhc_class must be class1, class2 or both"}
    try:
        result = predict_peptides(
            peptides,
            alleles,
            mhc_class=mhc_class,
            predictor="iedb",
            processing=bool(processing),
        )
    except (ValueError, RuntimeError) as error:
        return {"error": str(error)}
    return {
        "predictions": result["predictions"],
        "errors": result["errors"],
        "warning": "Binding prediction is not presentation or immunogenicity.",
    }


@server.tool()
def lookup_epitope(peptides: list[str]) -> dict:
    """Look up to 10 peptides in the IEDB T-cell assay database.

    A hit means the exact peptide sequence has been assayed before; it is not
    evidence that this candidate is a validated neoantigen. Requires network
    access to query-api.iedb.org.
    """
    from epitoperank.peptide import IedbClient, IedbError

    if not isinstance(peptides, list) or not peptides:
        return {"error": "peptides must be a non-empty list"}
    if len(peptides) > _MAX_PEPTIDES_LOOKUP:
        return {"error": f"at most {_MAX_PEPTIDES_LOOKUP} peptides per call"}
    try:
        matches = IedbClient().lookup_epitopes(peptides, limit=3)
    except (IedbError, ValueError) as error:
        return {"error": str(error)}
    return {
        "matches": matches,
        "note": (
            "An IEDB assay hit means the exact peptide was studied before; it "
            "does not establish presentation, immunogenicity or tumour specificity."
        ),
    }


@server.tool()
def copilot_tools(allow_network: bool = True) -> dict:
    """List the analysis copilot's tools and whether a model is configured."""
    from epitoperank.agent.copilot import status
    from epitoperank.config import load_prepared_settings

    settings, _ = load_prepared_settings()
    return status(settings, allow_network=allow_network)


@server.tool()
def ask_copilot(question: str, project_id: str = "", max_steps: int = 4,
                mode: str = "auto", allow_network: bool = True) -> dict:
    """Ask the tool-using analysis copilot about one project.

    Runs a bounded native-tool-calling loop over project memory (events,
    candidates, enrichment, quality), plus optional literature/gene/peptide
    tools. ``mode`` is ``react``, ``plan`` or ``auto``; ``plan`` adds a
    structured evidence plan, a critic review and at most one revision.
    """
    from epitoperank.agent.copilot import ask
    from epitoperank.config import load_prepared_settings

    if not isinstance(question, str) or not question.strip():
        return {"error": "question is required"}
    if mode not in {"auto", "react", "plan"}:
        return {"error": "mode must be auto, react or plan"}
    settings, _ = load_prepared_settings()
    answer = ask(question, settings, project_id=project_id or None,
                 max_steps=max(1, min(8, int(max_steps))), mode=mode,
                 allow_network=allow_network)
    return answer.as_dict()


@server.tool()
def literature_passages(query: str, max_articles: int = 2, max_passages: int = 4) -> dict:
    """Full-text literature passages (Europe PMC open access, local BM25).

    Returns extractive quotes with PMID/PMCID and section, so an answer can
    cite what a paper measured rather than only its title.
    """
    from epitoperank.knowledge.literature_rag import RagError, search_passages

    if not isinstance(query, str) or not query.strip():
        return {"error": "query is required"}
    try:
        return search_passages(query, max_articles=max(1, min(5, int(max_articles))),
                               max_passages=max(1, min(10, int(max_passages))))
    except RagError as error:
        return {"error": str(error)[:400]}


def main() -> None:
    # Match the CLI/desktop behaviour: a key stored in .env or 配置大模型.env
    # must also configure the copilot tools exposed over MCP.
    try:
        from epitoperank.llm.envfile import load_env_values

        load_env_values()
    except Exception:  # noqa: BLE001 - .env is optional
        pass
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

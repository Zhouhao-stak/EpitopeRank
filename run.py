#!/usr/bin/env python3
"""EpitopeRank command line interface.

Examples
--------
Run a full analysis::

    python run.py analyze --input examples/demo_rmats --query "分析RNA剪接变化"

List projects::

    python run.py projects

Show a project's workflow log::

    python run.py status --project-id SPN-XXXXXXXX

Serve the API (the browser UI is rendered at `/`)::

    python run.py serve --port 8800
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

# Fix Windows console encoding for Chinese characters
if sys.platform == "win32":
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
    except (AttributeError, LookupError):
        pass  # Fallback: keep default encoding

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _cmd_analyze(args: argparse.Namespace) -> int:
    from epitoperank.config import load_prepared_settings, load_settings
    from epitoperank.llm.client import describe_llm_mode
    from epitoperank.pipeline import run_analysis

    settings, _warnings = load_prepared_settings(args.config)
    agent_block = settings.agent
    if args.agent_mode:
        agent_block = dataclasses.replace(agent_block, mode=args.agent_mode)
    if args.autonomy:
        agent_block = dataclasses.replace(agent_block, autonomy=args.autonomy)
    if args.skills:
        agent_block = dataclasses.replace(
            agent_block,
            skills=dataclasses.replace(agent_block.skills, enabled=args.skills == "on"),
        )
    settings = dataclasses.replace(settings, agent=agent_block)
    print(f"[epitoperank] mode: {describe_llm_mode(settings)}")
    print(f"[epitoperank] engine: {'autonomous agent' if settings.agent.agentic else 'scripted team'}")
    print(
        f"[epitoperank] autonomy: {settings.agent.autonomy} "
        f"| external skills: {'on' if settings.agent.skills.enabled else 'off'} "
        f"| hypothesis tests: {'on' if settings.agent.hypothesis_testing else 'off'}"
    )
    print(f"[epitoperank] query: {args.query}")
    outcome = run_analysis(args.query, args.input, settings=settings, project_id=args.project_id,
                           output_root=args.out)
    summary = outcome.summary()
    print(f"[epitoperank] project: {summary['project_id']}")
    print(f"[epitoperank] dataset: {json.dumps(summary['dataset'], ensure_ascii=False)}")
    print(f"[epitoperank] validation: {json.dumps(summary['validation'], ensure_ascii=False)}")
    print(f"[epitoperank] team: mode={summary['mode']} reason={summary['stopped_reason']} tool_calls={summary['tool_calls']}")
    print(f"[epitoperank] top candidates:")
    for index, candidate in enumerate(summary["top_candidates"], start=1):
        gene = candidate["gene_symbol"] or candidate["gene_id"]
        print(
            f"  {index:>2}. {gene:<12} {candidate['event_type']:<5} "
            f"dPSI={candidate['delta_PSI']} FDR={candidate['FDR']} score={candidate['score']}"
        )
    if summary["enriched_terms"]:
        print(f"[epitoperank] enriched terms: {', '.join(summary['enriched_terms'])}")
    agent = summary.get("agent") or {}
    if agent:
        print(
            f"[epitoperank] agent: goal_satisfied={agent['goal_satisfied']} "
            f"steps={len(agent['steps'])} issues={len(agent['issues'])} "
            f"params={json.dumps(agent['params'], ensure_ascii=False)}"
        )
        for step in agent["steps"]:
            print(
                f"  {step['index'] + 1:>2}. [{step['source']:<11}] {step['action']:<28} "
                f"{step['status']:<7} {step['rationale'][:70]}"
            )
        for issue in agent["issues"]:
            print(f"  ! {issue['severity']:<7} {issue['code']}: {issue['message'][:90]}")
    print(f"[epitoperank] figures: {', '.join(summary['figures'])}")
    print(f"[epitoperank] report: {json.dumps(summary['report_paths'], ensure_ascii=False)}")
    print(f"[epitoperank] output dir: {summary['output_dir']}")
    return 0


def _cmd_replay(args):
    from epitoperank.config import load_prepared_settings
    from epitoperank.pipeline import run_analysis
    from epitoperank.llm.trace import ReplayError
    settings, _ = load_prepared_settings(args.config)
    settings = dataclasses.replace(settings, agent=dataclasses.replace(settings.agent, replay=args.trace))
    try:
        trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
        result = run_analysis(trace.get("meta", {}).get("query", ""), args.input,
                              settings=settings, output_root=args.out)
    except (ReplayError, ValueError, KeyError) as error:
        print(f"replay failed: {error}", file=sys.stderr)
        return 1
    print(f"replay verified: {result.output_dir}")
    return 0


def _cmd_compare(args):
    from epitoperank.llm.trace import compare
    differences = compare(args.trace_a, args.trace_b)
    print("; ".join(differences) if differences else "identical")
    return 1 if differences else 0


def _cmd_followup(args: argparse.Namespace) -> int:
    from epitoperank.config import (
        AgentSettings,
        load_prepared_settings,
        SkillSettings,
    )
    from epitoperank.pipeline import resume_analysis

    settings, _warnings = load_prepared_settings(args.config)
    agent_block: AgentSettings = settings.agent
    if args.autonomy:
        agent_block = dataclasses.replace(agent_block, autonomy=args.autonomy)
    if args.skills:
        agent_block = dataclasses.replace(
            agent_block,
            skills=SkillSettings(
                enabled=args.skills == "on",
                max_calls=agent_block.skills.max_calls,
                timeout=agent_block.skills.timeout,
            ),
        )
    settings = dataclasses.replace(settings, agent=agent_block)
    print(f"[epitoperank] resume: {args.project_id}")
    print(f"[epitoperank] autonomy: {settings.agent.autonomy} | skills: {'on' if settings.agent.skills.enabled else 'off'}")
    print(f"[epitoperank] query: {args.query}")
    try:
        outcome = resume_analysis(args.project_id, args.query, settings=settings)
    except ValueError as error:
        print(f"[epitoperank] error: {error}")
        return 1
    summary = outcome.summary()
    agent = summary.get("agent") or {}
    print(f"[epitoperank] resumed: mode={summary['mode']} reason={summary['stopped_reason']}")
    if agent:
        print(
            f"[epitoperank] agent: goal_satisfied={agent['goal_satisfied']} "
            f"steps={len(agent['steps'])} params={json.dumps(agent['params'], ensure_ascii=False)}"
        )
        for step in agent["steps"]:
            print(
                f"  {step['index'] + 1:>2}. [{step['source']:<11}] {step['action']:<28} "
                f"{step['status']:<7} {step['rationale'][:70]}"
            )
    print(f"[epitoperank] report: {json.dumps(summary['report_paths'], ensure_ascii=False)}")
    print(f"[epitoperank] output dir: {summary['output_dir']}")
    return 0


def _cmd_peptide(args: argparse.Namespace) -> int:
    """Predict, filter and rank MHC-I/II peptides."""
    from epitoperank.peptide import PeptideOptions, capabilities, run

    if args.hla_panel:
        from epitoperank.peptide.hla import panel

        alleles = panel(args.hla_panel)
    else:
        alleles = [item for item in (args.alleles or "").replace(";", ",").split(",") if item.strip()]
    if args.capabilities:
        print(json.dumps(capabilities(), ensure_ascii=False, indent=2))
        return 0
    if not args.out:
        print("[epitoperank] error: --out is required unless --capabilities is used")
        return 1
    options = PeptideOptions(
        alleles=[item.strip() for item in alleles],
        mhc_class=args.mhc_class,
        predictor=args.predictor,
        processing=not args.no_processing,
        stability=args.stability,
        mhcnp=args.mhcnp,
        lookup_epitopes=args.lookup_epitopes,
        self_fastas=args.fasta or [],
        class2_window=args.class2_window,
        max_predictions=args.max_predictions,
        cache=not args.no_cache,
    )
    if args.methods_class1:
        options.methods[1] = args.methods_class1
    if args.methods_class2:
        options.methods[2] = args.methods_class2
    if args.lengths:
        try:
            options.lengths = tuple(sorted({
                int(item) for item in args.lengths.replace(" ", "").split(",") if item
            }))
        except ValueError:
            print("[epitoperank] error: --lengths must be comma-separated integers, e.g. 8,9,10,11")
            return 1
        if not options.lengths or any(length < 8 or length > 11 for length in options.lengths):
            print("[epitoperank] error: CDS-mode --lengths must be within 8-11 (MHC-I peptides)")
            return 1
    try:
        result = run(output_dir=args.out, input_dir=args.input, cds_table=args.cds,
                     peptides=args.peptides, options=options)
    except (ValueError, OSError) as error:
        print(f"[epitoperank] error: {error}")
        return 1
    print(f"[epitoperank] candidates: {result['candidate_count']} "
          f"predictions: {result['prediction_count']} ranked: {result['ranked_count']}")
    print(f"[epitoperank] evidence tiers: {json.dumps(result['tiers'], ensure_ascii=False)}")
    for row in result["manifest"]["prediction_summary"]["method_labels"]:
        print(f"[epitoperank] model: {row}")
    if result["errors"]:
        print(f"[epitoperank] prediction errors: {len(result['errors'])}")
        for error in result["errors"][:5]:
            print(f"  ! {error.get('stage')}: {error.get('error')}")
    ranked_path = Path(result["output_dir"]) / "ranked_candidates.tsv"
    if ranked_path.is_file():
        import csv as _csv

        with ranked_path.open(encoding="utf-8") as handle:
            rows = list(_csv.DictReader(handle, delimiter="\t"))
        print("[epitoperank] top candidates:")
        for row in rows[:10]:
            print(f"  {row['rank']:>3}. {row['peptide']:<12} {row['best_allele']:<14} "
                  f"pct={row['percentile_rank']:<8} tier={row['evidence_tier']} "
                  f"score={row['composite_score']}")
    if args.json:
        print(json.dumps({key: value for key, value in result.items() if key != "manifest"},
                         ensure_ascii=False, indent=2))
    print(f"[epitoperank] output dir: {result['output_dir']}")
    return 0


def _cmd_projects(args: argparse.Namespace) -> int:
    from epitoperank.config import load_prepared_settings, load_settings
    from epitoperank.pipeline import list_projects

    settings, _warnings = load_prepared_settings(args.config)
    projects = list_projects(settings)
    if not projects:
        print("No projects yet.")
        return 0
    for project in projects:
        print(f"{project['project_id']}  {project['created_at']}  {project['name']}  {project['query'][:60]}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    from epitoperank.config import load_prepared_settings, load_settings
    from epitoperank.pipeline import project_status

    settings, _warnings = load_prepared_settings(args.config)
    payload = project_status(args.project_id, settings)
    if payload is None:
        print(f"Project {args.project_id} not found.")
        return 1
    for entry in payload["logs"]:
        print(f"{entry['created_at']}  [{entry['agent']}] {entry['action']} -> {entry['status']}")
        if entry["detail"]:
            print(f"    {entry['detail'][:200]}")
    for artifact in payload["artifacts"]:
        print(f"artifact: {artifact['kind']} -> {artifact['path']}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """启动 FastAPI 服务（Web UI 由该服务在 `/` 直接渲染）。

    旧版 `--ui` 会额外拉起 Streamlit 看板，该界面已整体移除；这里仍识别这个
    参数并给出提示，避免老脚本/老文档撞上 argparse 的 "unrecognized arguments"。
    """
    if getattr(args, "ui", False):
        print(
            "Streamlit 界面已移除。请改用 `python serve_ui.py`"
            "（浏览器打开 http://localhost:8800），或 `python run.py serve --api`。"
        )
        return 2

    import threading

    def start_api() -> None:
        """在当前线程内以前台方式运行 uvicorn，端口取自 --port。"""
        import uvicorn
        from epitoperank.api.app import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)

    thread = threading.Thread(target=start_api, daemon=True)
    thread.start()
    print(f"API server starting on http://{args.host}:{args.port}")

    # 主线程只负责等待与优雅退出；uvicorn 自己处理信号。
    try:
        thread.join()
    except KeyboardInterrupt:
        print("\nShutting down...")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="epitoperank", description="EpitopeRank CLI")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Run a full analysis")
    analyze.add_argument("--input", required=True, help="Input file or directory")
    analyze.add_argument("--query", required=True, help="Natural-language analysis goal")
    analyze.add_argument("--project-id", default=None, help="Reuse a project id")
    analyze.add_argument(
        "--agent-mode",
        choices=("agentic", "scripted"),
        default=None,
        help="agentic = autonomous self-deciding loop (default); scripted = legacy fixed flow",
    )
    analyze.add_argument(
        "--autonomy",
        choices=("auto", "assisted"),
        default=None,
        help="auto = the agent decides alone; assisted = confirm risky decisions (network calls, threshold relaxation)",
    )
    analyze.add_argument(
        "--skills",
        choices=("on", "off"),
        default=None,
        help="enable/disable the external knowledge skills (MyGene / PubMed / Enrichr / splice interpretation)",
    )
    analyze.add_argument("--out", default=None, help="Output project root; model trace recorded automatically")
    analyze.set_defaults(func=_cmd_analyze)

    followup = subparsers.add_parser(
        "followup", help="Resume a project with a follow-up query (multi-turn analysis)"
    )
    followup.add_argument("--project-id", required=True, help="An existing project id to continue")
    followup.add_argument("--query", required=True, help="Follow-up goal, e.g. 'zoom into TP53' or 'only SE events'")
    followup.add_argument(
        "--autonomy",
        choices=("auto", "assisted"),
        default=None,
        help="auto = the agent decides alone; assisted = confirm risky decisions",
    )
    followup.add_argument(
        "--skills",
        choices=("on", "off"),
        default=None,
        help="enable/disable the external knowledge skills",
    )
    followup.set_defaults(func=_cmd_followup)

    projects = subparsers.add_parser("projects", help="List projects")
    projects.set_defaults(func=_cmd_projects)

    status = subparsers.add_parser("status", help="Show a project's workflow log")
    status.add_argument("--project-id", required=True)
    status.set_defaults(func=_cmd_status)

    serve = subparsers.add_parser("serve", help="Serve the API (the web UI is served at /)")
    serve.add_argument("--api", action="store_true", help="兼容旧脚本：现在 serve 总是启动 API")
    serve.add_argument("--ui", action="store_true", help="已移除：旧 Streamlit 看板，传入会报错退出")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8800)
    serve.set_defaults(func=_cmd_serve)

    peptide = subparsers.add_parser(
        "peptide",
        help="Predict and rank MHC-I/II peptides from splice-derived candidates",
    )
    peptide.add_argument("--input", default=None, help="Project/event directory (CDS mode)")
    peptide.add_argument("--cds", default=None,
                         help="TSV/CSV with event_id, reference_cds, altered_cds, junction_nt")
    peptide.add_argument("--peptides", default=None,
                         help="Existing peptide table (TSV/CSV) or peptide FASTA")
    peptide.add_argument("--alleles", default=None,
                         help="Comma-separated HLA alleles, e.g. HLA-A*02:01,HLA-B*07:02")
    peptide.add_argument("--hla-panel", default=None,
                         choices=("class1_common", "class2_common"),
                         help="Use a bundled convenience panel instead of --alleles")
    peptide.add_argument("--mhc-class", default="both", choices=("class1", "class2", "both"))
    peptide.add_argument("--predictor", default="iedb", choices=("iedb", "local", "auto", "none"))
    peptide.add_argument("--methods-class1", default=None,
                         help="IEDB MHC-I method key (see `peptide --capabilities`)")
    peptide.add_argument("--methods-class2", default=None,
                         help="IEDB MHC-II method key (see `peptide --capabilities`)")
    peptide.add_argument("--no-processing", action="store_true",
                         help="Skip the IEDB proteasome/TAP processing prediction")
    peptide.add_argument("--stability", action="store_true", help="Add NetMHCstabpan-1.0")
    peptide.add_argument("--mhcnp", action="store_true", help="Add MHC-NP processing probability")
    peptide.add_argument("--lookup-epitopes", action="store_true",
                         help="Look the top peptides up in the IEDB assay database")
    peptide.add_argument("--fasta", action="append", default=[],
                         help="Normal protein FASTA for self/novelty filtering (repeatable)")
    peptide.add_argument("--class2-window", type=int, default=15,
                         help="Window length used for MHC-II prediction (11-30)")
    peptide.add_argument("--lengths", default=None,
                         help="CDS-mode peptide lengths within 8-11, e.g. 8,9,10,11")
    peptide.add_argument("--max-predictions", type=int, default=2000)
    peptide.add_argument("--no-cache", action="store_true", help="Bypass the on-disk IEDB cache")
    peptide.add_argument("--out", default=None, help="Output directory")
    peptide.add_argument("--json", action="store_true", help="Print the result summary as JSON")
    peptide.add_argument("--capabilities", action="store_true",
                         help="Print available methods, reference tables and limits, then exit")
    peptide.set_defaults(func=_cmd_peptide)

    replay = subparsers.add_parser("replay", help="Strict offline model/decision replay")
    replay.add_argument("--input", required=True)
    replay.add_argument("--trace", required=True)
    replay.add_argument("--out", required=True)
    replay.set_defaults(func=_cmd_replay)
    compare = subparsers.add_parser("compare", help="Compare steps, params, ranked results and report hashes")
    compare.add_argument("trace_a")
    compare.add_argument("trace_b")
    compare.set_defaults(func=_cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    # The desktop launcher and the API load the local .env automatically; the
    # CLI should behave the same way, otherwise a key pasted into the UI looks
    # "ignored" when the same project is analysed from a terminal.
    try:
        from epitoperank.llm.envfile import load_env_values

        load_env_values()
    except Exception:  # noqa: BLE001 - .env is optional
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

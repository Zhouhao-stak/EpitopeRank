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

Serve the API / dashboard::

    python run.py serve --api --port 8800
    python run.py serve --ui --port 8501
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
    outcome = run_analysis(args.query, args.input, settings=settings, project_id=args.project_id)
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


def _cmd_copilot(args: argparse.Namespace) -> int:
    """Ask the tool-using analysis copilot a question."""
    from epitoperank.agent.copilot import ask, status
    from epitoperank.config import load_prepared_settings

    settings, _warnings = load_prepared_settings(args.config)
    if args.tools:
        print(json.dumps(status(settings, project_id=args.project_id,
                                allow_network=not args.no_network),
                         ensure_ascii=False, indent=2))
        return 0
    if not args.message:
        print("[epitoperank] error: --message is required (or use --tools)")
        return 1

    def on_event(event: dict) -> None:
        if not args.stream:
            return
        name, data = event.get("event"), event.get("data") or {}
        if name == "plan":
            tools = [step.get("tool") for step in data.get("steps") or [] if step.get("tool")]
            print(f"[plan] {len(tools)} steps: {' -> '.join(tools)}")
        elif name == "tool_result":
            print(f"[tool] {data.get('tool')} ok={data.get('ok')} cached={data.get('cached')}")
        elif name in {"critique", "revision"}:
            print(f"[{name}] {json.dumps(data, ensure_ascii=False)[:200]}")

    try:
        answer = ask(args.message, settings, project_id=args.project_id,
                     max_steps=args.max_steps, force_offline=args.offline,
                     mode=args.mode, allow_network=not args.no_network,
                     use_cache=not args.no_cache, on_event=on_event)
    except (ValueError, RuntimeError) as error:
        print(f"[epitoperank] error: {error}")
        return 1
    print(answer.answer)
    print("")
    print(f"[epitoperank] mode={answer.mode} strategy={answer.strategy} steps={answer.steps} "
          f"tools={len(answer.tool_calls)} elapsed={answer.elapsed_seconds}s")
    if answer.plan:
        steps = [step.get("tool") or step.get("action") for step in answer.plan.get("steps") or []]
        print(f"[epitoperank] plan({answer.plan.get('source')}): {' -> '.join(str(s) for s in steps)}")
    for call in answer.tool_calls:
        cached = " (cache)" if call.get("cached") else ""
        print(f"  · {call['tool']}({json.dumps(call['arguments'], ensure_ascii=False)}) "
              f"-> {call['summary'][:80]}{cached}")
    if answer.usage:
        print(f"[epitoperank] tokens: {json.dumps(answer.usage, ensure_ascii=False)}")
    if answer.grounding:
        print(f"[epitoperank] grounding: {answer.grounding.get('severity')} "
              f"({answer.grounding.get('checked')} numbers checked, "
              f"{len(answer.grounding.get('unverified') or [])} unverified)")
    if answer.critique:
        print(f"[epitoperank] critique: {answer.critique.get('verdict')} "
              f"({len(answer.critique.get('issues') or [])} issues, "
              f"source={answer.critique.get('source')})")
    if args.json:
        print(json.dumps(answer.as_dict(), ensure_ascii=False, indent=2))
    return 0


def _cmd_eval_agent(args: argparse.Namespace) -> int:
    """Run the copilot golden-set evaluation."""
    from epitoperank.agent.evaluation import evaluate, load_cases, write_report
    from epitoperank.config import load_prepared_settings
    from epitoperank.llm.chat import ChatClient
    from epitoperank.pipeline import list_projects

    settings, _warnings = load_prepared_settings(args.config)
    project_id = args.project_id
    if not project_id:
        projects = list_projects(settings)
        project_id = str(projects[0].get("project_id") or "") if projects else None
    cases = load_cases(args.cases)
    factory = (lambda case: ChatClient(settings)) if args.mode == "live" else None
    payload = evaluate(
        cases, settings, project_id=project_id, chat_factory=factory,
        allow_network=args.allow_network and args.mode == "live",
    )
    paths = write_report(payload, args.out)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"[epitoperank] report: {paths['markdown']}")
    threshold = float(args.min_pass_rate)
    return 0 if payload["summary"]["pass_rate"] >= threshold else 1


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
    import threading
    
    def start_api():
        import uvicorn
        from epitoperank.api.app import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)
    
    def start_ui():
        import subprocess
        ui_path = Path(__file__).resolve().parent / "epitoperank" / "interface" / "streamlit_app.py"
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(ui_path), "--server.port", "8501", "--server.address", "0.0.0.0"]
        )
    
    threads = []
    if args.api:
        api_thread = threading.Thread(target=start_api, daemon=True)
        api_thread.start()
        threads.append(api_thread)
        print(f"API server starting on http://{args.host}:{args.port}")
    
    if args.ui:
        ui_thread = threading.Thread(target=start_ui, daemon=True)
        ui_thread.start()
        threads.append(ui_thread)
        print("Streamlit UI starting on http://0.0.0.0:8501")
    
    if not threads:
        print("Nothing to serve: pass --api or --ui.")
        return 1
    
    # Keep main thread alive
    try:
        for t in threads:
            t.join()
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

    serve = subparsers.add_parser("serve", help="Serve the API or the dashboard")
    serve.add_argument("--api", action="store_true", help="Serve the FastAPI application")
    serve.add_argument("--ui", action="store_true", help="Serve the Streamlit dashboard")
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

    copilot = subparsers.add_parser(
        "copilot",
        help="Ask the tool-using analysis copilot about a project (agentic mode)",
    )
    copilot.add_argument("--message", default=None, help="Analyst question")
    copilot.add_argument("--project-id", default=None, help="Project to analyse")
    copilot.add_argument("--max-steps", type=int, default=6, help="Model/tool loop budget (1-10)")
    copilot.add_argument("--mode", choices=("auto", "react", "plan"), default="auto",
                         help="auto = plan for long/multi-part questions; react = plain tool loop; "
                              "plan = plan + critic + one revision")
    copilot.add_argument("--no-network", action="store_true",
                         help="Disable literature/annotation/pathway/peptide tools")
    copilot.add_argument("--no-cache", action="store_true",
                         help="Bypass the persistent tool-result cache")
    copilot.add_argument("--stream", action="store_true",
                         help="Print plan/tool/critique events while the loop runs")
    copilot.add_argument("--offline", action="store_true",
                         help="Skip the model and print the deterministic briefing")
    copilot.add_argument("--tools", action="store_true", help="List tools and readiness, then exit")
    copilot.add_argument("--json", action="store_true", help="Print the full result as JSON")
    copilot.set_defaults(func=_cmd_copilot)

    eval_agent = subparsers.add_parser(
        "eval-agent",
        help="Run the copilot golden-set evaluation (scripted or live)",
    )
    eval_agent.add_argument("--cases", default=str(Path(__file__).resolve().parent
                                                   / "examples" / "agent_eval" / "golden.jsonl"))
    eval_agent.add_argument("--project-id", default=None)
    eval_agent.add_argument("--mode", choices=("scripted", "live"), default="scripted")
    eval_agent.add_argument("--allow-network", action="store_true")
    eval_agent.add_argument("--out", default=str(Path(__file__).resolve().parent / "out" / "agent_eval"))
    eval_agent.add_argument("--min-pass-rate", type=float, default=0.0)
    eval_agent.set_defaults(func=_cmd_eval_agent)
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

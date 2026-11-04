#!/usr/bin/env python3
"""Run the copilot evaluation golden set.

Examples
--------
Deterministic (no model, no network; always safe in CI)::

    python scripts/evaluate_copilot.py --demo

Live model regression run::

    python scripts/evaluate_copilot.py --project-id SPN-XXXX --mode live --allow-network
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from epitoperank.agent.evaluation import evaluate, load_cases, write_report  # noqa: E402
from epitoperank.config import load_prepared_settings  # noqa: E402
from epitoperank.llm.chat import ChatClient  # noqa: E402
from epitoperank.pipeline import list_projects, run_analysis  # noqa: E402


def resolve_project(settings, explicit: str | None, *, demo: bool) -> str | None:
    if explicit:
        return explicit
    projects = list_projects(settings)
    if projects:
        return str(projects[0].get("project_id") or "") or None
    if not demo:
        return None
    print("[eval] no project found; running the demo analysis to seed one...")
    outcome = run_analysis("分析RNA剪接变化", str(ROOT / "examples" / "demo_rmats"),
                           settings=settings)
    return outcome.summary().get("project_id")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path,
                        default=ROOT / "examples" / "agent_eval" / "golden.jsonl")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--mode", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--allow-network", action="store_true",
                        help="Live mode: let network tools run (slower, uses quota)")
    parser.add_argument("--demo", action="store_true",
                        help="Create a demo project when none exists")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "agent_eval")
    parser.add_argument("--min-pass-rate", type=float, default=0.0,
                        help="Exit non-zero when the pass rate is below this value")
    args = parser.parse_args(argv)

    settings, warnings = load_prepared_settings()
    for warning in warnings:
        print(f"[eval] warning: {warning}")
    project_id = resolve_project(settings, args.project_id, demo=args.demo)
    if project_id is None:
        print("[eval] no project available; project cases will fail. Use --demo to seed one.")
    else:
        print(f"[eval] project: {project_id}")

    cases = load_cases(args.cases)
    print(f"[eval] cases: {len(cases)} | mode: {args.mode} | network: {args.allow_network}")

    def progress(row: dict) -> None:
        mark = "PASS" if row.get("passed") else "FAIL"
        print(f"  [{mark}] {row.get('id'):<18} recall={row.get('tool_recall')} "
              f"precision={row.get('tool_precision')} grounding={row.get('grounding_ok')} "
              f"tokens={row.get('tokens')}")

    factory = (lambda case: ChatClient(settings)) if args.mode == "live" else None
    payload = evaluate(
        cases, settings, project_id=project_id, chat_factory=factory,
        allow_network=args.allow_network and args.mode == "live",
        progress=progress,
    )
    paths = write_report(payload, args.out)
    summary = payload["summary"]
    print("\n[eval] summary")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[eval] report: {paths['markdown']}")
    if summary["pass_rate"] < args.min_pass_rate:
        print(f"[eval] pass rate {summary['pass_rate']} < {args.min_pass_rate}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

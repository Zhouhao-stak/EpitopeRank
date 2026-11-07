"""Per-run model boundary and integrity-checked decision tape (no network on replay)."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACTIVE: ContextVar = ContextVar("model_trace", default=None)


class ReplayError(RuntimeError):
    """A trace cannot reproduce this run; never an advisory failure."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     default=str, separators=(",", ":")).encode()).hexdigest()


def file_hash(path: Path) -> str:
    # Same streaming SHA-256 algorithm used by input manifests.
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def fingerprints(path) -> dict:
    root = Path(path)
    files = sorted(root.rglob("*")) if root.is_dir() else [root]
    return {str(p.relative_to(root) if root.is_dir() else p.name): file_hash(p)
            for p in files if p.is_file()}


@dataclass
class ModelCallRecord:
    seq: int
    stage: str
    prompt_hash: str
    system: str
    user: str
    model: str
    temperature_effective: float | None
    max_tokens: int | None
    json_output: bool
    raw_response: str | None
    parsed: dict | None
    elapsed_ms: float
    retries: int
    timestamp: str


def model_request(enhancer, *, stage, **kwargs):
    """Use one recording boundary, including small injected completion clients."""
    trace = getattr(enhancer, "recorder", None) or ACTIVE.get()
    if trace:
        return trace.request(enhancer, dict(kwargs, stage=stage))
    return enhancer.complete(**kwargs)


class ModelTrace:
    def __init__(self, settings, replay=None):
        self.settings = settings
        self.replay = bool(replay)
        self.calls = []
        self.decisions = []
        self.cursor = self.decision_cursor = 0
        self.errors = []
        self.secrets = [str(v) for k, v in asdict(settings.llm).items()
                        if re.search(r"key|token|authorization|secret|password", k, re.I) and v]
        self.meta = {}
        self.expected = {}
        if replay:
            try:
                data = json.loads(Path(replay).read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                self.fail(f"cannot read model trace: {error}")
            if not isinstance(data, dict):
                self.fail("model trace must be a JSON object")
            self.expected = data
            self.meta = data.get("meta", {})
            self.calls = data.get("model_calls", [])
            self.decisions = self.meta.get("decisions", [])
            if self.meta.get("schema_version") != 1 or not self.meta.get("integrity"):
                self.fail("missing or unsupported model trace")
            if self.meta["integrity"] != self.checksum(data):
                self.fail("trace checksum mismatch")
            if not isinstance(self.calls, list) or not isinstance(self.decisions, list):
                self.fail("model calls and decisions must be lists")
            from .enrich import extract_json
            try:
                for i, call in enumerate(self.calls):
                    ModelCallRecord(**{key: call[key] for key in ModelCallRecord.__dataclass_fields__})
                    parsed = extract_json(call["raw_response"])
                    parsed = parsed if isinstance(parsed, dict) else None
                    if (call["seq"] != i or parsed != call["parsed"] or call["prompt_hash"] != hashlib.sha256(
                            (call["system"] + "\n" + call["user"]).encode()).hexdigest()):
                        self.fail(f"invalid model call sequence/prompt/response checksum: {i}")
                for item in self.decisions:
                    if not 0 <= item["begin"] <= item["end"] <= len(self.calls):
                        self.fail("invalid decision model-call range")
            except (KeyError, TypeError, ValueError) as error:
                self.fail(f"incomplete model trace: {error}")

    def clean(self, value):
        if isinstance(value, dict):
            return {k: self.clean(v.split("?", 1)[0].split("@")[-1] if k == "base_url" and isinstance(v, str) else v) for k, v in value.items()
                    if not re.fullmatch(r"(?:.*_)?(?:api_?key|access_token|refresh_token|token|authorization|password|secret)", str(k), re.I)}
        if isinstance(value, (list, tuple)):
            return [self.clean(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            value = re.sub(r"(?i)(authorization[\s\"']*[:=][\s\"']*(?:Bearer\s+)?)[^\s,;\"'}]+", r"\1[REDACTED]", value)
            return re.sub(r"(?i)((?:api[_-]?key|token)[\s\"']*[:=][\s\"']*)[^\s,;\"'}]+", r"\1[REDACTED]", value)
        return value

    def fail(self, message):
        self.errors.append({"error": message})
        raise ReplayError(message)

    @staticmethod
    def checksum(data):
        value = copy.deepcopy(data)
        value.get("meta", {}).pop("integrity", None)
        return digest(value)

    def request(self, enhancer, kwargs):
        from .enrich import extract_json
        from .client import effective_temperature
        stage = kwargs.pop("stage", None) or "enrichment:" + (kwargs.get("feature") or "generic")
        system, user = self.clean(kwargs["system"]), self.clean(kwargs["user"])
        prompt_hash = hashlib.sha256((system + "\n" + user).encode()).hexdigest()
        if self.replay:
            if self.cursor >= len(self.calls):
                self.fail(f"missing model call: {stage}")
            record = self.calls[self.cursor]
            if (record["stage"], record["prompt_hash"], record["max_tokens"], record["json_output"], record["model"]) != (
                    stage, prompt_hash, kwargs.get("max_tokens"), kwargs.get("json_output", False), kwargs.get("model") or enhancer.model):
                self.fail(f"model call order/prompt/parameters mismatch at seq {self.cursor}: {stage}")
            self.cursor += 1
            enhancer.calls.extend(copy.deepcopy(record.get("calls_added", [])))
            enhancer.errors.extend(copy.deepcopy(record.get("errors_added", [])))
            if enhancer.logger:
                for note in record.get("notes", []):
                    enhancer.logger(*note)
            return record["raw_response"]
        started = time.perf_counter()
        enhancer._trace_attempts = 0
        call_count, error_count = len(enhancer.calls), len(enhancer.errors)
        notes = []
        logger = enhancer.logger
        def capture(*args):
            notes.append(self.clean(args))
            if logger:
                logger(*args)
        enhancer.logger = capture
        try:
            response = enhancer.complete(**kwargs)
        finally:
            enhancer.logger = logger
        raw = self.clean(response)
        parsed = extract_json(raw)
        self.calls.append(asdict(ModelCallRecord(
            len(self.calls), stage, prompt_hash, system, user,
            kwargs.get("model") or enhancer.model,
            effective_temperature(enhancer.settings, tools_expected=True),
            kwargs.get("max_tokens"), kwargs.get("json_output", False), raw,
            parsed if isinstance(parsed, dict) else None,
            round((time.perf_counter() - started) * 1000, 3), max(0, enhancer._trace_attempts - 1),
            datetime.now(timezone.utc).isoformat())))
        self.calls[-1].update(calls_added=self.clean(enhancer.calls[call_count:]),
                              errors_added=self.clean(enhancer.errors[error_count:]), notes=notes)
        return response

    def decide(self, engine, original):
        if not self.replay:
            begin = len(self.calls)
            before = copy.deepcopy(engine.state.facts)
            before_params = copy.deepcopy(engine.state.params)
            decision = original()
            self.decisions.append(self.clean({"decision": decision.as_dict(), "begin": begin,
                "end": len(self.calls), "facts": {k: v for k, v in engine.state.facts.items()
                    if k not in before or before[k] != v},
                "params": {k: v for k, v in engine.state.params.items()
                           if k not in before_params or before_params[k] != v}}))
            # Do not retain mutable blackboard references.
            self.decisions[-1] = copy.deepcopy(self.decisions[-1])
            return decision
        from epitoperank.agent.decision import Decision
        if self.decision_cursor >= len(self.decisions):
            self.fail("missing recorded decision")
        item = self.decisions[self.decision_cursor]
        if self.cursor != item["begin"]:
            self.fail("decision/model call sequence mismatch")
        if any(c["stage"] not in {"model_plan", "insight"}
               for c in self.calls[self.cursor:item["end"]]):
            self.fail("unexpected model stage in decision")
        self.cursor = item["end"]
        self.decision_cursor += 1
        engine.state.facts.update(copy.deepcopy(item["facts"]))
        engine.state.params.update(copy.deepcopy(item["params"]))
        decision = Decision(**item["decision"])
        decision.source = "replay"
        return decision

    def finish(self):
        if self.replay and (self.cursor != len(self.calls) or self.decision_cursor != len(self.decisions)):
            self.fail("unconsumed model calls or decisions")


def traced_decision(method):
    @wraps(method)
    def wrapped(engine):
        trace = ACTIVE.get()
        return trace.decide(engine, lambda: method(engine)) if trace else method(engine)
    return wrapped


def compare(a, b):
    def load(path):
        p = Path(path)
        state_path = p / "agent_state.json" if p.is_dir() else p
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["_artifact_hashes"] = {kind: file_hash(state_path.parent / f"report.{kind}")
                                   for kind in data.get("meta", {}).get("reports", {})
                                   if (state_path.parent / f"report.{kind}").exists()}
        return data
    left, right = load(a), load(b)
    def steps(data):
        output = data.get("meta", {}).get("output_dir", "")
        def normal(value):
            return value.replace(output, "<OUTPUT>") if output and isinstance(value, str) else value
        return [{k: normal(v) for k, v in s.items() if k not in {"source", "seconds"}} for s in data.get("steps", [])]
    differences = []
    for label, data in (("left", left), ("right", right)):
        if data.get("errors") or data.get("replay_success") is False:
            differences.append(label + " run failed")
        for kind, actual in data["_artifact_hashes"].items():
            if actual != data["meta"]["reports"][kind]:
                differences.append(f"{label} report.{kind} modified: {actual[:12]}")
    for name, x, y in [("steps", steps(left), steps(right)), ("params", left.get("params"), right.get("params")),
                       ("ranked", left.get("meta", {}).get("ranked"), right.get("meta", {}).get("ranked")),
                       ("reports sha256", left.get("meta", {}).get("reports"), right.get("meta", {}).get("reports"))]:
        if x != y:
            differences.append(name + " differ")
    if not left.get("meta", {}).get("reports") or not right.get("meta", {}).get("reports"):
        differences.append("missing report hashes")
    return differences

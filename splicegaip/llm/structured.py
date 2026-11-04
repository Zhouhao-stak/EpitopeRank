"""Structured-output validation and numeric grounding for model replies.

Two cheap, high-value guardrails that make an LLM usable in a scientific
pipeline:

* :func:`validate_schema` — a small JSON-Schema subset checker, so a task can
  reject a malformed reply instead of writing it into a report;
* :func:`grounding_report` — finds numbers in generated prose that do not
  appear anywhere in the computed facts, which is where hallucinations hurt
  most ("an FDR of 0.003" when the table says 0.03).

Neither function is a correctness proof. They are *tripwires*: the UI and the
report can show "3 numbers unverified" and let the analyst decide.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Iterable, Mapping, Sequence

NUMBER_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w])")
YEAR_RANGE = (1900, 2100)
#: Numbers that are structural rather than measured (list indices, "top 10").
TRIVIAL = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 100.0}

_SCHEMA_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list, tuple),
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "null": (type(None),),
}


def validate_schema(payload: Any, schema: Mapping[str, Any], *, path: str = "$") -> list[str]:
    """Validate ``payload`` against a JSON-Schema subset.

    Supported keywords: ``type`` (string or list), ``required``,
    ``properties``, ``items``, ``enum``, ``minimum``, ``maximum``,
    ``minItems``, ``maxItems``. Unknown keywords are ignored on purpose: the
    goal is to catch malformed replies, not to re-implement jsonschema.
    """
    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None:
        types = [expected] if isinstance(expected, str) else list(expected)
        matched = False
        for name in types:
            python_types = _SCHEMA_TYPES.get(name)
            if python_types is None:
                continue
            if name in {"number", "integer"} and isinstance(payload, bool):
                continue
            if isinstance(payload, python_types):
                matched = True
                break
        if not matched:
            errors.append(f"{path}: expected {'|'.join(types)}")
            return errors

    if "enum" in schema and payload not in schema["enum"]:
        errors.append(f"{path}: value {payload!r} not in enum")

    if isinstance(payload, Mapping):
        for key in schema.get("required", []):
            if key not in payload:
                errors.append(f"{path}.{key}: required key missing")
        for key, child in (schema.get("properties") or {}).items():
            if key in payload:
                errors.extend(validate_schema(payload[key], child, path=f"{path}.{key}"))

    if isinstance(payload, (list, tuple)):
        if "minItems" in schema and len(payload) < int(schema["minItems"]):
            errors.append(f"{path}: fewer than minItems")
        if "maxItems" in schema and len(payload) > int(schema["maxItems"]):
            errors.append(f"{path}: more than maxItems")
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(payload):
                errors.extend(validate_schema(item, item_schema, path=f"{path}[{index}]"))

    if isinstance(payload, (int, float)) and not isinstance(payload, bool):
        if "minimum" in schema and payload < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and payload > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    return errors


def _collect_numbers(value: Any, out: set[float], depth: int = 0) -> None:
    if depth > 12:
        return
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            out.add(float(value))
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _collect_numbers(item, out, depth + 1)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_numbers(item, out, depth + 1)
        return
    if isinstance(value, str):
        for token in NUMBER_RE.findall(value):
            try:
                out.add(float(token))
            except ValueError:
                continue


def _collect_strings(value: Any, out: list[str], depth: int = 0) -> None:
    """Flatten the JSON text so identifier substrings count as grounded."""
    if depth > 12:
        return
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            out.append(str(key))
            _collect_strings(item, out, depth + 1)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_strings(item, out, depth + 1)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        out.append(repr(value))
    else:
        try:
            out.append(json.dumps(value, ensure_ascii=False, default=str))
        except (TypeError, ValueError):
            pass


def _close(a: float, b: float, tolerance: float) -> bool:
    if a == b:
        return True
    scale = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / scale <= tolerance


def grounding_report(text: str, facts: Any, *, tolerance: float = 0.01) -> dict[str, Any]:
    """Check whether numbers in ``text`` are present in ``facts``.

    A number counts as grounded when it, or the same value scaled by 100
    (percentage vs fraction), appears in the fact payload within
    ``tolerance``, or when the literal token appears in the serialised facts
    (so "GRCh38", "HLA-A*02:01", "4.1" method versions are not flagged).
    """
    numbers = [float(token) for token in NUMBER_RE.findall(text or "")]
    fact_numbers: set[float] = set()
    _collect_numbers(facts, fact_numbers)
    fact_text = " ".join(_collect_strings_list(facts))

    unverified: list[str] = []
    checked = 0
    for value in numbers:
        if value in TRIVIAL:
            continue
        checked += 1
        if YEAR_RANGE[0] <= value <= YEAR_RANGE[1] and value == int(value):
            continue
        if any(_close(value, known, tolerance) for known in fact_numbers):
            continue
        if any(_close(value / 100.0, known, tolerance) for known in fact_numbers):
            continue
        token = _format_number(value)
        if token and token in fact_text:
            continue
        unverified.append(token)

    ratio = 1.0 if checked == 0 else round(1 - len(unverified) / checked, 3)
    severity = "ok" if not unverified else ("review" if len(unverified) <= 2 else "warn")
    return {
        "checked": checked,
        "unverified": unverified,
        "grounded_ratio": ratio,
        "severity": severity,
        "note": "Unverified numbers may be hallucinated; confirm them against the tables.",
    }


def _collect_strings_list(value: Any) -> list[str]:
    out: list[str] = []
    _collect_strings(value, out)
    return out


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


#: Schema used by the copilot's final structured self-check (optional).
ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["answer"],
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "used_tools": {"type": "array", "items": {"type": "string"}},
        "caveats": {"type": "array", "items": {"type": "string"}},
    },
}


def coerce_answer(payload: Any, fallback_text: str = "") -> dict[str, Any]:
    """Normalise an optional structured answer payload."""
    if not isinstance(payload, Mapping):
        return {"answer": fallback_text, "confidence": "", "used_tools": [], "caveats": []}
    answer = payload.get("answer")
    return {
        "answer": str(answer) if isinstance(answer, str) and answer.strip() else fallback_text,
        "confidence": str(payload.get("confidence") or ""),
        "used_tools": [str(item) for item in payload.get("used_tools") or [] if isinstance(item, str)],
        "caveats": [str(item) for item in payload.get("caveats") or [] if isinstance(item, str)],
    }


def summarise_errors(errors: Sequence[str], limit: int = 5) -> str:
    return "; ".join(errors[:limit])


def iter_floats(value: Any) -> Iterable[float]:
    """Yield every finite number inside a nested payload (debug helper)."""
    found: set[float] = set()
    _collect_numbers(value, found)
    yield from sorted(found)

"""Tests for structured-output validation and numeric grounding."""

from __future__ import annotations

from epitoperank.llm.structured import (
    ANSWER_SCHEMA,
    coerce_answer,
    grounding_report,
    validate_schema,
)


class TestValidateSchema:
    def test_nested_object_passes(self) -> None:
        payload = {"answer": "ok", "used_tools": ["project_overview"]}
        assert validate_schema(payload, ANSWER_SCHEMA) == []

    def test_missing_required_and_wrong_type(self) -> None:
        errors = validate_schema({"used_tools": "not-a-list"}, ANSWER_SCHEMA)
        assert any("required" in item for item in errors)
        assert any("used_tools" in item for item in errors)

    def test_enum_and_bounds(self) -> None:
        schema = {"type": "object", "properties": {
            "mode": {"type": "string", "enum": ["a", "b"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        }}
        errors = validate_schema({"mode": "c", "limit": 99}, schema)
        assert any("enum" in item for item in errors)
        assert any("maximum" in item for item in errors)

    def test_boolean_is_not_a_number(self) -> None:
        errors = validate_schema({"value": True}, {"type": "object", "properties": {
            "value": {"type": "number"}}})
        assert errors


class TestGrounding:
    def test_grounded_numbers(self) -> None:
        report = grounding_report(
            "FDR 0.01, ΔPSI 0.35 across 600 events.",
            {"fdr": 0.01, "delta_psi": 0.35, "events": 600},
        )
        assert report["unverified"] == []
        assert report["severity"] == "ok"
        assert report["grounded_ratio"] == 1.0

    def test_percentage_matches_fraction(self) -> None:
        report = grounding_report("约 35% 的事件上调", {"fraction": 0.35})
        assert report["unverified"] == []

    def test_hallucinated_number_is_flagged(self) -> None:
        report = grounding_report("FDR 0.0001 in 4242 events.", {"fdr": 0.01, "events": 600})
        assert "4242" in report["unverified"]
        assert report["severity"] in {"review", "warn"}

    def test_trivial_and_year_numbers_are_ignored(self) -> None:
        report = grounding_report("Top 10 events from 2019.", {"events": 600})
        assert report["unverified"] == []

    def test_identifier_tokens_count_as_grounded(self) -> None:
        report = grounding_report("HLA-A*02:01 predicted NetMHCpan-4.1",
                                  {"allele": "HLA-A*02:01", "method": "NetMHCpan-4.1"})
        assert report["unverified"] == []


class TestCoerceAnswer:
    def test_falls_back_to_text(self) -> None:
        assert coerce_answer(None, "plain")["answer"] == "plain"

    def test_structured_payload(self) -> None:
        result = coerce_answer({"answer": "a", "confidence": "high",
                                "used_tools": ["x"], "caveats": ["y"]})
        assert result == {"answer": "a", "confidence": "high",
                          "used_tools": ["x"], "caveats": ["y"]}

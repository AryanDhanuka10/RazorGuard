"""
agents/eval_harness.py

LLM Investigation Agent evaluation (EVALUATION_PLAN.md Section 5): evidence
faithfulness, unsupported-claim rate, schema validity, insufficient-evidence
correctness — computed over 20-30 manually reviewed cases drawn from actual
usage (real flagged clusters + dev-scenario synthetic cases).

*** WHAT THIS FILE DOES AND DOES NOT DO ***
This module computes the four metrics from a list of (evidence_bundle,
agent_response, is_actually_weak_case) records — from ANY source. The
functions here are fully tested against canned/synthetic records
(tests/test_eval_harness.py) and are real, working code.

What this file does NOT contain: a populated 20-30 case result set from the
REAL Investigation Agent. Producing that requires actually calling the live
Anthropic API (agents/investigate.py) against real clusters and dev-scenario
synthetic cases, reviewing each response by hand for unsupported claims, and
recording is_actually_weak_case labels by human judgment — none of which is
possible in this sandbox (no ANTHROPIC_API_KEY, see REPO_STATE.md). Treat
`run_full_evaluation`'s output as the reporting mechanism to run once real
agent responses exist, not as evidence that it already has been.
"""
from __future__ import annotations

from dataclasses import dataclass

from agents.schema import validate_investigation_result, SchemaValidationError


@dataclass
class ReviewedCase:
    case_id: str
    evidence_bundle: dict
    raw_agent_response: dict  # the model's raw JSON output, before validation
    # Human-reviewed label: does each claim in the response actually trace to
    # the cited evidence field's real content? This requires human judgment,
    # not just "does the cited field exist" (agents/schema.py already checks
    # that structurally) — this module cannot fill it in automatically.
    claims_grounded: list[bool] | None = None
    # Human judgment: was this actually a weak/ambiguous case where
    # insufficient_evidence would have been the right call?
    is_actually_weak_case: bool | None = None


def compute_schema_validity_rate(cases: list[ReviewedCase]) -> dict:
    valid, invalid_reasons = 0, []
    for c in cases:
        try:
            validate_investigation_result(c.raw_agent_response)
            valid += 1
        except SchemaValidationError as e:
            invalid_reasons.append({"case_id": c.case_id, "reason": str(e)})
    return {
        "schema_validity_rate": valid / len(cases) if cases else None,
        "num_cases": len(cases),
        "invalid_cases": invalid_reasons,
    }


def compute_evidence_faithfulness(cases: list[ReviewedCase]) -> dict:
    """Requires cases where claims_grounded has been filled in by human
    review — cannot be computed for cases missing that label."""
    reviewed = [c for c in cases if c.claims_grounded is not None]
    if not reviewed:
        return {
            "evidence_faithfulness_rate": None,
            "unsupported_claim_rate": None,
            "note": "no cases have human-reviewed claims_grounded labels yet",
        }
    total_claims = sum(len(c.claims_grounded) for c in reviewed)
    grounded_claims = sum(sum(c.claims_grounded) for c in reviewed)
    return {
        "evidence_faithfulness_rate": grounded_claims / total_claims if total_claims else None,
        "unsupported_claim_rate": 1 - (grounded_claims / total_claims) if total_claims else None,
        "num_cases_reviewed": len(reviewed),
        "total_claims": total_claims,
    }


def compute_insufficient_evidence_correctness(cases: list[ReviewedCase]) -> dict:
    """Of cases a human judged to actually be weak, what fraction did the
    agent correctly call insufficient_evidence on (rather than escalating)?"""
    weak_cases = [c for c in cases if c.is_actually_weak_case is True]
    if not weak_cases:
        return {"insufficient_evidence_correctness": None, "note": "no cases labeled as actually-weak yet"}
    correct = sum(1 for c in weak_cases if c.raw_agent_response.get("verdict") == "insufficient_evidence")
    return {
        "insufficient_evidence_correctness": correct / len(weak_cases),
        "num_weak_cases": len(weak_cases),
    }


def run_full_evaluation(cases: list[ReviewedCase]) -> dict:
    return {
        "num_cases": len(cases),
        "meets_20_to_30_case_target": 20 <= len(cases) <= 30,
        "schema_validity": compute_schema_validity_rate(cases),
        "evidence_faithfulness": compute_evidence_faithfulness(cases),
        "insufficient_evidence_correctness": compute_insufficient_evidence_correctness(cases),
    }

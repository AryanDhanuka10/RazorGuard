"""
agents/schema.py

Structured output contract for the Investigation Agent (ARCHITECTURE.md
Section 4): verdict (escalate / insufficient_evidence), confidence,
evidence-grounded bullet explanation, a per-claim citation to a specific
evidence field. "insufficient_evidence" is a first-class, expected output,
not a failure mode.

This module has no LLM dependency — it's the pure-Python validation layer
that any agent response (real or, for testing, a canned/mocked one) must
pass before being accepted downstream.
"""
from __future__ import annotations

from dataclasses import dataclass, field


VALID_VERDICTS = ("escalate", "insufficient_evidence")

# The exact set of top-level evidence-bundle keys a citation is allowed to
# point at (agents/evidence_builder.py's output keys). A citation to anything
# else is malformed — this is what makes "no claim without a citation" and
# "per-claim citation to a specific evidence field" (ARCHITECTURE.md Section 4)
# mechanically checkable rather than just a prompt instruction.
VALID_CITATION_FIELDS = {
    "cluster_members",
    "shared_identifier_facts",
    "temporal_pattern",
    "transaction_risk_scores",
    "cluster_score_breakdown",
}


@dataclass
class EvidenceCitedClaim:
    claim: str
    cited_field: str


@dataclass
class InvestigationResult:
    verdict: str
    confidence: float
    claims: list[EvidenceCitedClaim] = field(default_factory=list)
    raw_response: dict | None = None


class SchemaValidationError(ValueError):
    pass


def validate_investigation_result(raw: dict) -> InvestigationResult:
    """
    Validates a raw (parsed-JSON) agent response against the contract.
    Raises SchemaValidationError with a specific reason on any violation —
    callers (agents/investigate.py) must not silently accept a malformed
    response (EVALUATION_PLAN.md Section 5: "Schema validity" is a scored
    metric, not an afterthought).
    """
    if "verdict" not in raw:
        raise SchemaValidationError("missing 'verdict'")
    if raw["verdict"] not in VALID_VERDICTS:
        raise SchemaValidationError(f"verdict must be one of {VALID_VERDICTS}, got {raw['verdict']!r}")

    if "confidence" not in raw:
        raise SchemaValidationError("missing 'confidence'")
    confidence = raw["confidence"]
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        raise SchemaValidationError(f"confidence must be a number in [0,1], got {confidence!r}")

    claims_raw = raw.get("claims", [])
    if raw["verdict"] == "escalate" and not claims_raw:
        raise SchemaValidationError("verdict 'escalate' requires at least one cited claim")

    claims = []
    for i, c in enumerate(claims_raw):
        if "claim" not in c or "cited_field" not in c:
            raise SchemaValidationError(f"claim {i} missing 'claim' or 'cited_field'")
        if c["cited_field"] not in VALID_CITATION_FIELDS:
            raise SchemaValidationError(
                f"claim {i} cites unknown field {c['cited_field']!r} — must be one of {VALID_CITATION_FIELDS}"
            )
        claims.append(EvidenceCitedClaim(claim=c["claim"], cited_field=c["cited_field"]))

    return InvestigationResult(
        verdict=raw["verdict"], confidence=float(confidence), claims=claims, raw_response=raw
    )

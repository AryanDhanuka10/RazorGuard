"""
policy/engine.py

Deterministic policy engine (ARCHITECTURE.md Section 6): 4 tiers
(low/medium/high/critical), human approval required above low, NO
auto-block or auto-reversal at ANY tier, ever. This is the sourced official
Track 2 disqualification rule — not a discretionary design note, and this
module is a pure function so its guardrail test (tests/test_policy_guardrail.py)
can act as an unconditional release gate.

Nothing in this module performs a state-changing action itself — it only
returns a decision for a human (or the backend's audit-log writer) to act on.
ARCHITECTURE.md Section 2: policy/ "Does not own: Any language generation."
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PolicyTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyAction(str, Enum):
    NO_ACTION = "no_action"
    FLAG_FOR_REVIEW = "flag_for_review"
    ESCALATE_FOR_APPROVAL = "escalate_for_approval"
    # Note: there is deliberately no AUTO_BLOCK or AUTO_REVERSE value in this
    # enum at all — not merely unused. Adding one would itself violate the
    # guardrail this module exists to enforce.


@dataclass(frozen=True)
class PolicyDecision:
    tier: PolicyTier
    action: PolicyAction
    requires_human_approval: bool
    reason: str


# Tier boundaries on the normalized [0,1] cluster_score (graph/scoring.py).
# Tunable, but the STRUCTURE (4 tiers, no tier below "flag" ever auto-acts,
# no tier above "low" skips human approval) is the non-negotiable part.
TIER_THRESHOLDS = {
    PolicyTier.LOW: 0.0,
    PolicyTier.MEDIUM: 0.4,
    PolicyTier.HIGH: 0.6,
    PolicyTier.CRITICAL: 0.8,
}


def classify_tier(cluster_score: float) -> PolicyTier:
    if cluster_score >= TIER_THRESHOLDS[PolicyTier.CRITICAL]:
        return PolicyTier.CRITICAL
    if cluster_score >= TIER_THRESHOLDS[PolicyTier.HIGH]:
        return PolicyTier.HIGH
    if cluster_score >= TIER_THRESHOLDS[PolicyTier.MEDIUM]:
        return PolicyTier.MEDIUM
    return PolicyTier.LOW


def decide(cluster_score: float) -> PolicyDecision:
    """
    PURE FUNCTION — no side effects, no I/O, no state-changing action. This is
    what tests/test_policy_guardrail.py exercises exhaustively as a release
    gate: for ANY float input, this function must never return an action that
    autonomously blocks or reverses a transaction. There is no code path here
    that could return such an action, because PolicyAction has no such value
    — this isn't an "it happens not to return that" guarantee, it's structural.
    """
    if not (0.0 <= cluster_score <= 1.0):
        raise ValueError("cluster_score must be in [0,1]")

    tier = classify_tier(cluster_score)

    if tier == PolicyTier.LOW:
        return PolicyDecision(
            tier=tier,
            action=PolicyAction.NO_ACTION,
            requires_human_approval=False,
            reason="Score below the flagging threshold — no action taken.",
        )
    if tier == PolicyTier.MEDIUM:
        return PolicyDecision(
            tier=tier,
            action=PolicyAction.FLAG_FOR_REVIEW,
            requires_human_approval=True,
            reason="Score in the medium tier — flagged for human review, no automatic action.",
        )
    # HIGH and CRITICAL both escalate for human approval — the only
    # difference is urgency/prioritization, never autonomy. Section 6 is
    # explicit: "No auto-block or auto-reversal at any tier, ever."
    return PolicyDecision(
        tier=tier,
        action=PolicyAction.ESCALATE_FOR_APPROVAL,
        requires_human_approval=True,
        reason=f"Score in the {tier.value} tier — escalated for human approval before any action is taken.",
    )

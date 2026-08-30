"""
tests/test_policy_guardrail.py

THE GUARDRAIL TEST. Per ARCHITECTURE.md Section 6 / DAILY_BUILD_PLAN.md Day 4:
"a pytest suite that functions as a release gate ... This test is never
weakened, skipped, or modified to make a build pass."

If a future change to policy/engine.py ever causes this file to need editing
to pass, that is the signal to fix the change, not this test.
"""
import itertools

import pytest

from policy.engine import decide, PolicyAction, PolicyDecision, classify_tier, PolicyTier


NEVER_ALLOWED_ACTIONS = {"auto_block", "auto_reverse", "auto_block_transaction", "auto_reversal"}


def test_policy_action_enum_has_no_auto_block_or_reverse_value():
    """Structural guarantee, not a behavioral one: the enum itself must not
    contain an auto-block/auto-reverse value. This is stronger than testing
    that decide() never RETURNS one — it makes such a value impossible to add
    without this test catching it immediately."""
    all_values = {a.value for a in PolicyAction}
    for forbidden in NEVER_ALLOWED_ACTIONS:
        assert forbidden not in all_values


@pytest.mark.parametrize("score", [round(x * 0.01, 2) for x in range(0, 101)])
def test_decide_never_returns_auto_block_or_reverse_across_full_score_range(score):
    """Exhaustive sweep across the entire valid [0,1] range in 0.01
    increments (101 cases) — for ANY input, decide() must never authorize an
    autonomous block or reversal."""
    decision = decide(score)
    assert decision.action in {
        PolicyAction.NO_ACTION,
        PolicyAction.FLAG_FOR_REVIEW,
        PolicyAction.ESCALATE_FOR_APPROVAL,
    }
    assert decision.action.value not in NEVER_ALLOWED_ACTIONS


def test_every_tier_above_low_requires_human_approval():
    for score in [0.41, 0.61, 0.81, 0.99, 1.0]:
        decision = decide(score)
        if decision.tier != PolicyTier.LOW:
            assert decision.requires_human_approval is True


def test_low_tier_never_requires_approval_but_also_never_auto_acts():
    decision = decide(0.1)
    assert decision.tier == PolicyTier.LOW
    assert decision.requires_human_approval is False
    assert decision.action == PolicyAction.NO_ACTION


def test_boundary_values_0_and_1_do_not_crash_or_auto_act():
    for score in [0.0, 1.0]:
        decision = decide(score)
        assert decision.action.value not in NEVER_ALLOWED_ACTIONS


def test_out_of_range_scores_raise_rather_than_silently_clamp_and_act():
    """An out-of-range score must fail loudly (ValueError), never be silently
    clamped into some tier and acted upon — silent clamping could mask an
    upstream bug that feeds a malformed score into the policy engine."""
    with pytest.raises(ValueError):
        decide(-0.1)
    with pytest.raises(ValueError):
        decide(1.1)


def test_decide_is_a_pure_function_same_input_same_output():
    """No hidden state, no randomness, no I/O — required for this to function
    as a reliable release gate at all."""
    results = [decide(0.55) for _ in range(50)]
    assert all(r == results[0] for r in results)


def test_classify_tier_is_monotonic_non_decreasing():
    """Higher score can never map to a lower tier."""
    tier_order = {PolicyTier.LOW: 0, PolicyTier.MEDIUM: 1, PolicyTier.HIGH: 2, PolicyTier.CRITICAL: 3}
    scores = [round(x * 0.01, 2) for x in range(0, 101)]
    tiers = [tier_order[classify_tier(s)] for s in scores]
    for a, b in itertools.pairwise(tiers):
        assert b >= a


def test_no_policy_action_value_contains_the_substring_auto_combined_with_block_or_reverse():
    """Belt-and-suspenders lexical check across ALL current and any future
    accidentally-added enum values — catches near-miss names too (e.g.
    'auto_blocking', 'system_auto_reversal') that the exact-match set above
    might not anticipate verbatim."""
    for action in PolicyAction:
        v = action.value.lower()
        assert not ("auto" in v and ("block" in v or "revers" in v))

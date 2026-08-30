"""
backend/exposure.py

Estimated At-Risk Exposure formula (EVALUATION_PLAN.md Section 7):

    Estimated At-Risk Exposure = cluster_fraud_probability
                                * cluster_transaction_value
                                * recoverability_assumption

All three inputs are shown wherever this number is displayed — never a bare
figure. "Loss prevented" is never used anywhere in this codebase: no
intervention against real money has ever been deployed by this system.

Lives in backend/, not frontend/, so the frontend can never compute or
reformat this number itself (ARCHITECTURE.md Section 5a) — the number the
investigator sees is guaranteed to be the number that gets logged.
"""
from __future__ import annotations


def compute_estimated_exposure(
    cluster_fraud_probability: float,
    cluster_transaction_value: float,
    recoverability_assumption: float,
) -> dict:
    """
    recoverability_assumption is a labeled SCENARIO ASSUMPTION (EVALUATION_PLAN.md
    Section 6/7), never presented as a real Razorpay operating figure. Callers
    must pass an explicit value — no silent default — so every exposure figure
    carries its assumption visibly (see frontend/case_detail.py for how this is
    surfaced to the investigator).
    """
    if not (0.0 <= cluster_fraud_probability <= 1.0):
        raise ValueError("cluster_fraud_probability must be in [0,1]")
    if not (0.0 <= recoverability_assumption <= 1.0):
        raise ValueError("recoverability_assumption must be in [0,1] (it is a scenario assumption, not a real rate)")
    if cluster_transaction_value < 0:
        raise ValueError("cluster_transaction_value cannot be negative")

    exposure = cluster_fraud_probability * cluster_transaction_value * recoverability_assumption
    return {
        "estimated_at_risk_exposure": exposure,
        "cluster_fraud_probability": cluster_fraud_probability,
        "cluster_transaction_value": cluster_transaction_value,
        "recoverability_assumption": recoverability_assumption,
        "label": "Estimated At-Risk Exposure — a scenario estimate, never 'loss prevented'",
    }

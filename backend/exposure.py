"""
backend/exposure.py

Estimated At-Risk Exposure formula (EVALUATION_PLAN.md Section 7):

    Estimated At-Risk Exposure = model_risk_proxy
                                * cluster_transaction_value
                                * recoverability_assumption

All three inputs are returned in this function's result and must be shown
wherever the number is displayed -- never a bare figure.

*** NAMING NOTE -- read before renaming this back to cluster_fraud_probability ***
The parameter is `model_risk_proxy`, NOT `cluster_fraud_probability`. This was
a real semantic bug (caught by external review): callers pass `transaction_risk`
-- the MEAN of individual transactions' XGBoost predicted probabilities across
a cluster's members (graph/scoring.py). Averaging per-transaction model scores
does not, by itself, produce a calibrated "probability that this coordinated
cluster is fraudulent" -- that would require demonstrating the model is
calibrated AND justifying the transaction-level-probability ->
cluster-level-probability aggregation, neither of which has been done here.
EVALUATION_PLAN.md Section 7 itself draws this exact distinction: "Risk Score
!= Fraud Probability != Estimated At-Risk Exposure != Loss Prevented." Calling
this input `cluster_fraud_probability` was violating that discipline in the
code even though the surrounding prose respected it. Fixed by renaming the
input (and its exposed key in the result dict) to `model_risk_proxy`, and
updating the label to say so explicitly -- this is Option A (relabel honestly)
over Option B (build and justify a calibrated probability), since there is no
calibration evidence yet to support Option B.

"Loss prevented" is never used anywhere in this codebase: no intervention
against real money has ever been deployed. Lives in backend/, not frontend/,
so the frontend can never compute or reformat this number itself
(ARCHITECTURE.md Section 5a) -- the number the investigator sees is
guaranteed to be the number that gets logged.
"""
from __future__ import annotations


def compute_estimated_exposure(
    model_risk_proxy: float,
    cluster_transaction_value: float,
    recoverability_assumption: float,
) -> dict:
    """
    recoverability_assumption is a labeled SCENARIO ASSUMPTION (EVALUATION_PLAN.md
    Section 6/7), never presented as a real Razorpay operating figure. Callers
    must pass an explicit value -- no silent default -- so every exposure figure
    carries its assumption visibly (see frontend/case_detail.py for how this is
    surfaced to the investigator).

    model_risk_proxy is NOT a calibrated fraud probability -- see module
    docstring. It is whatever risk signal the caller has (e.g. mean member
    transaction risk from Layer A), used as a proxy input to a labeled
    scenario estimate, not asserted to be a true probability of anything.
    """
    if not (0.0 <= model_risk_proxy <= 1.0):
        raise ValueError("model_risk_proxy must be in [0,1]")
    if not (0.0 <= recoverability_assumption <= 1.0):
        raise ValueError("recoverability_assumption must be in [0,1] (it is a scenario assumption, not a real rate)")
    if cluster_transaction_value < 0:
        raise ValueError("cluster_transaction_value cannot be negative")

    exposure = model_risk_proxy * cluster_transaction_value * recoverability_assumption
    return {
        "estimated_at_risk_exposure": exposure,
        "model_risk_proxy": model_risk_proxy,
        "cluster_transaction_value": cluster_transaction_value,
        "recoverability_assumption": recoverability_assumption,
        "label": (
            "Estimated At-Risk Exposure -- a scenario estimate using a model risk "
            "proxy (NOT a calibrated cluster fraud probability), never 'loss prevented'"
        ),
    }
"""
backend/api.py

API surface (ARCHITECTURE.md Section 3):
POST /transactions/ingest, POST /graph/build, GET /clusters, GET /clusters/{id},
POST /clusters/{id}/investigate, GET /cases, GET /cases/{id},
POST /cases/{id}/approve, POST /cases/{id}/reject, GET /metrics, GET /health.

No PUT/DELETE /audit* route exists at all — absent from this router by
design, not merely unused (verified by test_no_audit_mutation_routes_exist
in tests/test_api.py).

This module owns orchestration across data/graph/ml/agents/policy — it does
NOT duplicate their business logic (ARCHITECTURE.md Section 2: backend/ "Does
not own: Business-logic duplication").

*** VERIFICATION STATUS ***
Fully testable in-process via FastAPI's TestClient — no live server, network,
or Postgres required for these tests, and they DO run for real in this
sandbox (tests/test_api.py). The one exception: /clusters/{id}/investigate
calls the Investigation Agent, which needs a live Anthropic API key
(agents/investigate.py) — that endpoint's HTTP wiring is tested with the
agent call mocked, not live.
"""
from __future__ import annotations

import pandas as pd
from fastapi import FastAPI, HTTPException

from backend.audit import get_connection, append_audit_entry, get_audit_trail
from backend.exposure import compute_estimated_exposure
from policy.engine import decide

app = FastAPI(title="RazorGuard API")

# In-memory application state for this reference implementation. A real
# deployment would load these from the artifacts produced by the Day 1-3
# pipeline (parquet files / a proper feature store), not recompute them
# per-request — this is intentionally the same data-loading pattern the
# Streamlit frontend uses (frontend/app.py, frontend/case_detail.py).
_state: dict = {"clusters": None, "scored": None, "edges": None, "rep": None, "risk": None, "entity_amt": None, "audit_conn": None}


def load_state(data_dir: str = "data") -> None:
    _state["clusters"] = pd.read_parquet(f"{data_dir}/clusters_full.parquet")
    _state["scored"] = pd.read_parquet(f"{data_dir}/scored_clusters.parquet")
    _state["edges"] = pd.read_parquet(f"{data_dir}/qualified_edges_full.parquet")
    _state["rep"] = pd.read_parquet(f"{data_dir}/entity_representative_view.parquet")
    _state["risk"] = pd.read_parquet(f"{data_dir}/entity_risk_scores.parquet")["risk_score"]
    _state["entity_amt"] = pd.read_parquet(f"{data_dir}/entity_total_amt.parquet")["total_transaction_amt"]
    _state["audit_conn"] = get_connection()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transactions/ingest")
def ingest_transactions():
    """Skeleton per DAILY_BUILD_PLAN.md Day 1 — the real ingestion pipeline
    (data/canonicalize.py) is run offline as a batch job in this reference
    implementation, not synchronously per-request. This endpoint exists to
    satisfy the API surface contract; wiring it to a real upload path is a
    reasonable next step, not done here."""
    raise HTTPException(status_code=501, detail="Batch ingestion pipeline runs offline; see data/canonicalize.py")


@app.post("/graph/build")
def build_graph():
    """Same pattern as /transactions/ingest — the real graph pipeline
    (graph/relationships.py, graph/edges.py, graph/cluster.py) is a batch job
    in this reference implementation."""
    raise HTTPException(status_code=501, detail="Batch graph pipeline runs offline; see graph/ modules")


@app.get("/clusters")
def list_clusters(limit: int = 50):
    if _state["scored"] is None:
        raise HTTPException(status_code=503, detail="state not loaded — call load_state() first")
    top = _state["scored"].sort_values("cluster_score", ascending=False).head(limit)
    return top[["cluster_id", "size", "cluster_score"]].to_dict(orient="records")


@app.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: str):
    if _state["scored"] is None:
        raise HTTPException(status_code=503, detail="state not loaded — call load_state() first")
    row = _state["scored"][_state["scored"]["cluster_id"] == cluster_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"cluster {cluster_id} not found")
    row = row.iloc[0]
    members = list(row["members"])
    # Real cluster transaction value — this used to be hardcoded to 0.0, which
    # meant this endpoint always reported zero exposure regardless of the
    # cluster's actual value, while frontend/dashboard.py computed the real
    # figure independently. That was a genuine drift between the API and the
    # UI that ARCHITECTURE.md Section 5a explicitly says must never happen.
    cluster_value = float(_state["entity_amt"].reindex(members).dropna().sum())
    exposure = compute_estimated_exposure(
        cluster_fraud_probability=float(row["transaction_risk"]),
        cluster_transaction_value=cluster_value,
        recoverability_assumption=0.3,
    )
    return {
        "cluster_id": cluster_id,
        "size": int(row["size"]),
        "cluster_score": float(row["cluster_score"]),
        "members": members,
        "score_breakdown": {
            "relationship_concentration": float(row["relationship_concentration"]),
            "transaction_risk": float(row["transaction_risk"]),
            "temporal_coordination": float(row["temporal_coordination"]),
            "structural_anomaly": float(row["structural_anomaly"]),
            "exposure": float(row["exposure"]),
        },
        "estimated_exposure": exposure,
    }


@app.post("/clusters/{cluster_id}/investigate")
def investigate(cluster_id: str):
    """Triggers the Investigation Agent (agents/investigate.py). Requires a
    real ANTHROPIC_API_KEY — not available in this sandbox (see
    agents/investigate.py module docstring). Writes the result to the audit
    log regardless of verdict."""
    from agents.investigate import investigate_cluster

    if _state["scored"] is None:
        raise HTTPException(status_code=503, detail="state not loaded — call load_state() first")
    if cluster_id not in set(_state["scored"]["cluster_id"]):
        raise HTTPException(status_code=404, detail=f"cluster {cluster_id} not found")

    try:
        result = investigate_cluster(
            cluster_id, _state["scored"], _state["edges"], _state["rep"], _state["risk"]
        )
    except Exception as e:
        # A missing/invalid API key (or any other agent-side failure) used to
        # bubble up as an opaque 500. Surface it explicitly instead — this is
        # the actual exception, not a fabricated message, but framed so a
        # caller can tell "the agent isn't configured" from "something is
        # actually broken".
        raise HTTPException(
            status_code=503,
            detail=(
                f"Investigation Agent call failed: {e}. This commonly means no valid "
                "LLM API key is configured (see agents/investigate.py's module docstring)."
            ),
        )
    row = _state["scored"][_state["scored"]["cluster_id"] == cluster_id].iloc[0]
    policy_decision = decide(float(row["cluster_score"]))

    append_audit_entry(
        _state["audit_conn"],
        case_id=cluster_id,
        model_risk_outputs={"transaction_risk": float(row["transaction_risk"])},
        evidence_used={"cluster_id": cluster_id},
        agent_output={"verdict": result.verdict, "confidence": result.confidence},
        policy_decision={"tier": policy_decision.tier.value, "action": policy_decision.action.value},
    )
    return {
        "cluster_id": cluster_id,
        "verdict": result.verdict,
        "confidence": result.confidence,
        "claims": [{"claim": c.claim, "cited_field": c.cited_field} for c in result.claims],
        "policy_decision": {
            "tier": policy_decision.tier.value,
            "action": policy_decision.action.value,
            "requires_human_approval": policy_decision.requires_human_approval,
        },
    }


@app.get("/cases")
def list_cases():
    """A 'case' in this reference implementation is any cluster_id that has
    an audit trail (i.e. has been investigated at least once)."""
    if _state["audit_conn"] is None:
        raise HTTPException(status_code=503, detail="state not loaded — call load_state() first")
    rows = _state["audit_conn"].execute("SELECT DISTINCT case_id FROM audit_logs").fetchall()
    return [r[0] for r in rows]


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    if _state["audit_conn"] is None:
        raise HTTPException(status_code=503, detail="state not loaded — call load_state() first")
    trail = get_audit_trail(_state["audit_conn"], case_id)
    if not trail:
        raise HTTPException(status_code=404, detail=f"case {case_id} not found")
    return trail


@app.post("/cases/{case_id}/approve")
def approve_case(case_id: str):
    """Human approval — the ONLY way any escalated case moves forward. This
    endpoint records a human_action; it never itself blocks or reverses
    anything (policy/engine.py never returns such an action to act on)."""
    trail = get_audit_trail(_state["audit_conn"], case_id)
    if not trail:
        raise HTTPException(status_code=404, detail=f"case {case_id} not found")
    last = trail[-1]
    append_audit_entry(
        _state["audit_conn"],
        case_id=case_id,
        model_risk_outputs={},
        evidence_used={},
        agent_output=None,
        policy_decision={},
        human_action={"decision": "approved"},
    )
    return {"case_id": case_id, "human_action": "approved"}


@app.post("/cases/{case_id}/reject")
def reject_case(case_id: str):
    trail = get_audit_trail(_state["audit_conn"], case_id)
    if not trail:
        raise HTTPException(status_code=404, detail=f"case {case_id} not found")
    append_audit_entry(
        _state["audit_conn"],
        case_id=case_id,
        model_risk_outputs={},
        evidence_used={},
        agent_output=None,
        policy_decision={},
        human_action={"decision": "rejected"},
    )
    return {"case_id": case_id, "human_action": "rejected"}


@app.get("/metrics")
def metrics():
    if _state["scored"] is None:
        raise HTTPException(status_code=503, detail="state not loaded — call load_state() first")
    return {
        "total_clusters": len(_state["scored"]),
        "mean_cluster_score": float(_state["scored"]["cluster_score"].mean()),
    }


# NOTE: there is deliberately no @app.put/@app.delete route anywhere in this
# file for /audit* or anything else touching the audit log — see module
# docstring and tests/test_api.py::test_no_audit_mutation_routes_exist.

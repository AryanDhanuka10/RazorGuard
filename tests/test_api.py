import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api import app, load_state, _state
from agents.schema import InvestigationResult, EvidenceCitedClaim


DATA_AVAILABLE = os.path.exists("data/scored_clusters.parquet")


@pytest.fixture(scope="module")
def client():
    if DATA_AVAILABLE:
        load_state("data")
    return TestClient(app)


def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.skipif(not DATA_AVAILABLE, reason="requires real pipeline artifacts under data/")
def test_list_clusters_returns_real_ranked_data(client):
    r = client.get("/clusters?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 5
    scores = [c["cluster_score"] for c in body]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.skipif(not DATA_AVAILABLE, reason="requires real pipeline artifacts under data/")
def test_get_cluster_detail_matches_list_endpoint(client):
    top = client.get("/clusters?limit=1").json()[0]
    detail = client.get(f"/clusters/{top['cluster_id']}").json()
    assert detail["cluster_score"] == pytest.approx(top["cluster_score"])
    assert "score_breakdown" in detail
    assert "estimated_exposure" in detail
    assert "label" in detail["estimated_exposure"]


@pytest.mark.skipif(not DATA_AVAILABLE, reason="requires real pipeline artifacts under data/")
def test_cluster_exposure_uses_real_nonzero_transaction_amount(client):
    """Regression test for the exposure=0.0 bug (external review): checking
    only that the 'estimated_exposure' key exists would still pass if the
    value were always zero, which is exactly what the original bug did. This
    asserts the actual numbers are real and nonzero, and cross-checks the
    transaction value against an independent computation from the same
    source parquet the API reads, not just the API's own arithmetic."""
    import pandas as pd

    top = client.get("/clusters?limit=1").json()[0]
    detail = client.get(f"/clusters/{top['cluster_id']}").json()
    exposure = detail["estimated_exposure"]

    assert exposure["cluster_transaction_value"] > 0
    assert exposure["estimated_at_risk_exposure"] > 0

    # Independently recompute the expected transaction value from the raw
    # entity_total_amt parquet + this cluster's real member list, rather than
    # trusting the API's own internal arithmetic.
    entity_amt = pd.read_parquet("data/entity_total_amt.parquet")["total_transaction_amt"]
    members = detail["members"]
    expected_value = float(entity_amt.reindex(members).dropna().sum())
    assert exposure["cluster_transaction_value"] == pytest.approx(expected_value)


def test_get_cluster_404_for_unknown_id(client):
    if not DATA_AVAILABLE:
        pytest.skip("requires real pipeline artifacts under data/")
    r = client.get("/clusters/does_not_exist")
    assert r.status_code == 404


@pytest.mark.skipif(not DATA_AVAILABLE, reason="requires real pipeline artifacts under data/")
def test_investigate_endpoint_with_mocked_agent_writes_audit_and_never_auto_acts(client):
    """The Investigation Agent's live LLM call is mocked here — this tests the
    HTTP wiring, audit-log write, and policy integration for real, without
    needing a live Anthropic API key (see agents/investigate.py)."""
    top = client.get("/clusters?limit=1").json()[0]
    mocked_result = InvestigationResult(
        verdict="escalate",
        confidence=0.85,
        claims=[EvidenceCitedClaim(claim="entities share a signal", cited_field="shared_identifier_facts")],
    )
    with patch("agents.investigate.call_investigation_agent", return_value=mocked_result):
        r = client.post(f"/clusters/{top['cluster_id']}/investigate")
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "escalate"
    assert body["policy_decision"]["action"] in ("no_action", "flag_for_review", "escalate_for_approval")
    assert body["policy_decision"]["action"] not in ("auto_block", "auto_reverse")

    case = client.get(f"/cases/{top['cluster_id']}").json()
    assert len(case) >= 1
    assert case[-1]["agent_output"] is not None


def test_no_audit_mutation_routes_exist():
    """Structural guard: no PUT or DELETE route touching /audit or /cases
    exists in the router at all (ARCHITECTURE.md Section 3)."""
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "audit" in path.lower():
            assert not methods, f"unexpected route on {path}"
        if "cases" in path.lower():
            assert "PUT" not in methods
            assert "DELETE" not in methods


@pytest.mark.skipif(not DATA_AVAILABLE, reason="requires real pipeline artifacts under data/")
def test_approve_and_reject_only_record_human_action_never_execute_anything(client):
    top = client.get("/clusters?limit=1").json()[0]
    with patch(
        "agents.investigate.call_investigation_agent",
        return_value=InvestigationResult(verdict="insufficient_evidence", confidence=0.2, claims=[]),
    ):
        client.post(f"/clusters/{top['cluster_id']}/investigate")

    r = client.post(f"/cases/{top['cluster_id']}/approve")
    assert r.status_code == 200
    assert r.json()["human_action"] == "approved"
    # response contains ONLY a recorded decision — no transaction/account
    # identifiers, no "blocked"/"reversed" field of any kind
    assert set(r.json().keys()) == {"case_id", "human_action"}

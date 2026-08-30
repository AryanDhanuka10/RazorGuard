import pandas as pd
import pytest

from agents.evidence_builder import build_evidence_bundle
from agents.schema import validate_investigation_result, SchemaValidationError


def _fixture():
    scored = pd.DataFrame(
        {
            "cluster_id": ["c1"],
            "members": [{"A", "B", "C"}],
            "cluster_score": [0.75],
            "relationship_concentration": [0.6],
            "transaction_risk": [0.4],
            "temporal_coordination": [0.1],
            "structural_anomaly": [0.5],
            "exposure": [0.3],
        }
    )
    edges = pd.DataFrame(
        {
            "entity_a": ["A", "A"],
            "entity_b": ["B", "C"],
            "edge_evidence_score": [0.5, 0.4],
            "signal_types": [["device_info"], ["device_info", "card_combo"]],
        }
    )
    rep = pd.DataFrame({"pseudo_entity_id": ["A", "B", "C"], "transaction_dt": [100, 200, 50000]})
    risk = pd.Series({"A": 0.8, "B": 0.6, "C": 0.7})
    return scored, edges, rep, risk


def test_build_evidence_bundle_contains_only_allowed_fields():
    scored, edges, rep, risk = _fixture()
    bundle = build_evidence_bundle("c1", scored, edges, rep, risk)
    assert bundle["cluster_id"] == "c1"
    assert set(bundle["cluster_members"]) == {"A", "B", "C"}
    assert bundle["cluster_size"] == 3
    assert len(bundle["shared_identifier_facts"]) == 2  # device_info and card_combo
    note = bundle["terminology_note"].lower()
    if "fraud ring" in note:
        assert "never" in note  # only mentioned to explicitly disclaim it
    assert "coordinated suspicious cluster" in note


def test_build_evidence_bundle_raises_on_unknown_cluster():
    scored, edges, rep, risk = _fixture()
    with pytest.raises(ValueError):
        build_evidence_bundle("nonexistent", scored, edges, rep, risk)


def test_shared_identifier_facts_use_approved_language():
    scored, edges, rep, risk = _fixture()
    bundle = build_evidence_bundle("c1", scored, edges, rep, risk)
    descriptions = [f["description"] for f in bundle["shared_identifier_facts"]]
    assert any("device-information signal" in d for d in descriptions)
    assert not any("same device" in d.lower() for d in descriptions)


# --- Schema validation with MOCKED/CANNED responses (no live API call) ---


def test_valid_escalate_response_passes():
    raw = {
        "verdict": "escalate",
        "confidence": 0.8,
        "claims": [{"claim": "3 entities share a device signal", "cited_field": "shared_identifier_facts"}],
    }
    result = validate_investigation_result(raw)
    assert result.verdict == "escalate"
    assert len(result.claims) == 1


def test_valid_insufficient_evidence_with_no_claims_passes():
    raw = {"verdict": "insufficient_evidence", "confidence": 0.3, "claims": []}
    result = validate_investigation_result(raw)
    assert result.verdict == "insufficient_evidence"


def test_escalate_with_no_claims_is_rejected():
    raw = {"verdict": "escalate", "confidence": 0.9, "claims": []}
    with pytest.raises(SchemaValidationError):
        validate_investigation_result(raw)


def test_invalid_verdict_value_rejected():
    raw = {"verdict": "block_transaction", "confidence": 0.9, "claims": []}
    with pytest.raises(SchemaValidationError):
        validate_investigation_result(raw)


def test_citation_to_unknown_field_rejected():
    raw = {
        "verdict": "escalate",
        "confidence": 0.9,
        "claims": [{"claim": "something", "cited_field": "my_own_intuition"}],
    }
    with pytest.raises(SchemaValidationError):
        validate_investigation_result(raw)


def test_confidence_out_of_range_rejected():
    raw = {"verdict": "insufficient_evidence", "confidence": 1.5, "claims": []}
    with pytest.raises(SchemaValidationError):
        validate_investigation_result(raw)


def test_missing_verdict_key_rejected():
    with pytest.raises(SchemaValidationError):
        validate_investigation_result({"confidence": 0.5})

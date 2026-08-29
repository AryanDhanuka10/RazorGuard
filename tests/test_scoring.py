import pandas as pd

from graph.scoring import (
    compute_hybrid_cluster_score,
    apply_minimum_evidence_filter,
    DEFAULT_WEIGHTS,
    weight_sensitivity_check,
)


def _fixture():
    clusters = pd.DataFrame(
        {
            "cluster_id": ["c1", "c2", "c3"],
            "members": [{"A", "B", "C"}, {"D", "E"}, {"F", "G", "H", "I"}],
            "size": [3, 2, 4],
        }
    )
    edges = pd.DataFrame(
        {
            "entity_a": ["A", "A", "B", "D", "F", "F", "G"],
            "entity_b": ["B", "C", "C", "E", "G", "H", "I"],
            "edge_evidence_score": [0.5, 0.4, 0.6, 0.3, 0.5, 0.5, 0.5],
            "signal_types": [
                ["device_info"],
                ["device_info", "card_combo"],
                ["device_info"],
                ["addr1"],
                ["card_combo"],
                ["card_combo"],
                ["card_combo"],
            ],
        }
    )
    entity_risk = pd.Series({"A": 0.9, "B": 0.8, "C": 0.7, "D": 0.1, "E": 0.2, "F": 0.5, "G": 0.5, "H": 0.5, "I": 0.5})
    entity_dt = pd.Series({"A": 100, "B": 105, "C": 110, "D": 100, "E": 500000, "F": 0, "G": 0, "H": 0, "I": 0})
    entity_amt = pd.Series({"A": 100, "B": 200, "C": 300, "D": 10, "E": 20, "F": 1000, "G": 1000, "H": 1000, "I": 1000})
    return clusters, edges, entity_risk, entity_dt, entity_amt


def test_all_components_in_unit_interval():
    clusters, edges, risk, dt, amt = _fixture()
    scored = compute_hybrid_cluster_score(clusters, edges, risk, dt, amt, total_entity_count=20)
    for col in ["relationship_concentration", "transaction_risk", "temporal_coordination", "structural_anomaly", "exposure"]:
        assert scored[col].between(0, 1).all()


def test_weights_sum_to_one():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_high_risk_cluster_scores_higher_than_low_risk_all_else_equal():
    clusters, edges, risk, dt, amt = _fixture()
    scored = compute_hybrid_cluster_score(clusters, edges, risk, dt, amt, total_entity_count=20)
    c1_risk = scored.loc[scored["cluster_id"] == "c1", "transaction_risk"].iloc[0]
    c2_risk = scored.loc[scored["cluster_id"] == "c2", "transaction_risk"].iloc[0]
    assert c1_risk > c2_risk  # A,B,C have high risk scores; D,E have low


def test_minimum_evidence_filter_drops_singletons_and_disconnected():
    clusters = pd.DataFrame(
        {"cluster_id": ["c1", "c2"], "members": [{"A", "B"}, {"C"}], "size": [2, 1]}
    )
    edges = pd.DataFrame(
        {
            "entity_a": ["A"],
            "entity_b": ["B"],
            "edge_evidence_score": [0.5],
            "signal_types": [["device_info"]],
        }
    )
    filtered = apply_minimum_evidence_filter(clusters, edges, min_members=2, min_independent_relationships=1)
    assert list(filtered["cluster_id"]) == ["c1"]


def test_weight_sensitivity_check_runs_and_returns_expected_keys():
    clusters, edges, risk, dt, amt = _fixture()
    scored = compute_hybrid_cluster_score(clusters, edges, risk, dt, amt, total_entity_count=20)
    result = weight_sensitivity_check(scored, DEFAULT_WEIGHTS, perturbation=0.3, top_k=2)
    assert "transaction_risk_up" in result
    assert 0.0 <= result["transaction_risk_up"]["top_k_overlap_fraction"] <= 1.0

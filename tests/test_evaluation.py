import pandas as pd

from graph.evaluation import (
    compute_cluster_fraud_labels,
    label_relevant,
    precision_at_k,
    recall_at_k,
    lift_over_baseline,
    run_layer_b1,
)


def test_precision_recall_at_k_basic():
    ranking = ["a", "b", "c", "d", "e"]
    relevant = {"a", "c", "z"}
    assert precision_at_k(ranking, relevant, k=3) == 2 / 3
    assert recall_at_k(ranking, relevant, k=3) == 2 / 3  # a,c found out of {a,c,z}


def test_lift_over_baseline_handles_zero_baseline():
    assert lift_over_baseline(0.5, 0.0) == float("inf")
    assert lift_over_baseline(0.0, 0.0) == 1.0


def test_compute_cluster_fraud_labels_concentration():
    clusters = pd.DataFrame({"cluster_id": ["c1"], "members": [{"A", "B"}]})
    fraud_count = pd.Series({"A": 2, "B": 0})
    txn_count = pd.Series({"A": 4, "B": 4})
    labels = compute_cluster_fraud_labels(clusters, fraud_count, txn_count)
    assert labels.loc[0, "fraud_txn_count"] == 2
    assert labels.loc[0, "total_txn_count"] == 8
    assert labels.loc[0, "fraud_concentration"] == 0.25


def test_label_relevant_either_condition():
    labels = pd.DataFrame(
        {
            "cluster_id": ["c1", "c2", "c3"],
            "fraud_txn_count": [1, 0, 0],
            "fraud_concentration": [0.0, 0.6, 0.1],
        }
    )
    relevant = label_relevant(labels, min_fraud_txn_count=1, min_concentration=0.5)
    assert list(relevant) == [True, True, False]


def test_run_layer_b1_reports_lift_and_never_claims_ring_ground_truth():
    scored_hybrid = pd.DataFrame({"cluster_id": ["c1", "c2"], "cluster_score": [0.9, 0.1]})
    labels = pd.DataFrame(
        {"cluster_id": ["c1", "c2"], "fraud_txn_count": [1, 0], "fraud_concentration": [1.0, 0.0]}
    )
    results = run_layer_b1(
        scored_hybrid,
        baseline_a_ranking=["c2", "c1"],
        baseline_b_ranking=["c1", "c2"],
        baseline_c_ranking=["c1", "c2"],
        cluster_fraud_labels=labels,
        k=2,
    )
    assert "NOT ring ground truth" in results["_meta"]["label_type"]
    assert results["hybrid_final"]["precision_at_k"] == 0.5  # only c1 is relevant, top-2 includes c2 too
    assert "lift_over_baseline_a" in results["hybrid_final"]

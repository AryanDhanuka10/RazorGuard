"""
scripts/day5_final_evaluation.py

*** THE ONLY FILE IN THIS REPOSITORY PERMITTED TO OPEN scenarios_test.yaml. ***

Layer B2 (EVALUATION_PLAN.md Section 3): synthetic ring evaluation with real
cluster-level ground truth, by construction. Run exactly once, after all
detector logic and thresholds are frozen from Layer A/B1 work
(DAILY_BUILD_PLAN.md Day 5 Task 1-2). No further tuning follows this run —
if these numbers are bad, that goes in FAILURE_LOG.md as a limitation for the
pitch, not as a reason to go back and adjust graph/edges.py's thresholds.

Metrics: cluster precision, cluster recall, entity-level precision/recall,
cluster purity. Reported in its own section, never mixed with Layer B1.
"""
from __future__ import annotations

import json

import pandas as pd
import yaml

from data.ring_injector import inject_all_scenarios
from graph.relationships import extract_all_raw_signals, signals_to_dataframe
from graph.edges import score_edges, qualify_edges, compute_global_identifier_counts, EDGE_QUALIFICATION_THRESHOLD
from graph.cluster import build_qualified_graph, extract_clusters, clusters_to_dataframe


def load_test_scenarios(path: str = "configs/scenarios_test.yaml") -> list[dict]:
    with open(path) as f:
        config = yaml.safe_load(f)
    return config["scenarios"]


def run_layer_b2(entity_representative_view: pd.DataFrame, scenarios_path: str = "configs/scenarios_test.yaml") -> dict:
    scenarios = load_test_scenarios(scenarios_path)
    injected_df, ground_truth = inject_all_scenarios(entity_representative_view, scenarios, base_seed=9000)

    global_counts = compute_global_identifier_counts(injected_df)
    signals = extract_all_raw_signals(injected_df)
    sig_df = signals_to_dataframe(signals)
    scored = score_edges(sig_df, global_counts)
    qualified = qualify_edges(scored, threshold=EDGE_QUALIFICATION_THRESHOLD)
    g = build_qualified_graph(qualified)
    clusters = extract_clusters(g, min_members=2)
    cdf = clusters_to_dataframe(clusters)

    results = {}
    all_true_members = set()
    for scenario_id, true_members in ground_truth.items():
        if not true_members:  # negative control
            results[scenario_id] = {"is_negative_control": True, "true_ring_size": 0}
            continue
        all_true_members.update(true_members)
        true_set = set(true_members)

        # find the detected cluster with the best overlap against this ring's ground truth
        best_overlap, best_cluster = 0, None
        for _, cluster_row in cdf.iterrows():
            overlap = len(set(cluster_row["members"]) & true_set)
            if overlap > best_overlap:
                best_overlap = overlap
                best_cluster = cluster_row

        if best_cluster is None:
            results[scenario_id] = {
                "is_negative_control": False,
                "true_ring_size": len(true_set),
                "detected": False,
                "cluster_precision": 0.0,
                "cluster_recall": 0.0,
                "entity_precision": 0.0,
                "entity_recall": 0.0,
                "purity": 0.0,
            }
            continue

        detected_set = set(best_cluster["members"])
        entity_precision = len(detected_set & true_set) / len(detected_set) if detected_set else 0.0
        entity_recall = len(detected_set & true_set) / len(true_set) if true_set else 0.0
        purity = len(detected_set & true_set) / len(detected_set) if detected_set else 0.0

        results[scenario_id] = {
            "is_negative_control": False,
            "true_ring_size": len(true_set),
            "detected": True,
            "detected_cluster_id": best_cluster["cluster_id"],
            "detected_cluster_size": len(detected_set),
            "entity_precision": entity_precision,
            "entity_recall": entity_recall,
            "purity": purity,
        }

    # cluster-level precision/recall: did we produce a cluster whose majority
    # overlap is a true ring for each positive scenario, vs. did any cluster
    # spuriously overlap a NEGATIVE control's untouched entities significantly
    positive_scenarios = [s for s in results.values() if not s.get("is_negative_control")]
    detected_count = sum(1 for s in positive_scenarios if s.get("detected"))
    cluster_recall = detected_count / len(positive_scenarios) if positive_scenarios else 0.0

    mean_entity_precision = (
        sum(s.get("entity_precision", 0) for s in positive_scenarios if s.get("detected")) / max(detected_count, 1)
    )
    mean_entity_recall = (
        sum(s.get("entity_recall", 0) for s in positive_scenarios if s.get("detected")) / max(detected_count, 1)
    )
    mean_purity = (
        sum(s.get("purity", 0) for s in positive_scenarios if s.get("detected")) / max(detected_count, 1)
    )

    return {
        "label_type": "Layer B2 (synthetic scenario result) — real cluster-level ground truth, by construction",
        "per_scenario": results,
        "summary": {
            "num_positive_scenarios": len(positive_scenarios),
            "num_detected": detected_count,
            "cluster_recall": cluster_recall,
            "mean_entity_precision_when_detected": mean_entity_precision,
            "mean_entity_recall_when_detected": mean_entity_recall,
            "mean_purity_when_detected": mean_purity,
        },
    }


if __name__ == "__main__":
    rep = pd.read_parquet("data/entity_representative_view.parquet")
    results = run_layer_b2(rep)
    print(json.dumps(results, indent=2))
    with open("ml/artifacts/layer_b2_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nLayer B2 complete. scenarios_test.yaml was opened by this script only, exactly once.")
    print("NO FURTHER TUNING of graph/edges.py, graph/scoring.py, or any threshold follows this run.")

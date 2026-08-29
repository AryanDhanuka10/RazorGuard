"""
graph/evaluation.py

Layer B1: real-data cluster prioritization using a DERIVED PROXY from
transaction-level fraud labels (EVALUATION_PLAN.md Section 2). This is never
described as ring ground truth — IEEE-CIS has none.

Proxy definition (documented, not hidden): a cluster is "relevant" if it
contains >= N member-transactions with isFraud=1, OR its fraud-label
concentration exceeds a stated threshold. N and the threshold are chosen on
the development split only.

Systems compared, all producing a ranked list of candidate clusters:
- Baseline A: rank by total cluster transaction value
- Baseline B: rank by maximum member transaction risk
- Baseline C: rank by graph-structural score alone (graph/baseline_c.py)
- Final: normalized hybrid cluster score (graph/scoring.py)
"""
from __future__ import annotations

import pandas as pd

# Documented proxy parameters — DAY-1/2 STARTING VALUES, must actually be
# selected on the development split before being treated as final (see
# select_proxy_params_on_dev below); not hardcoded truths.
PROXY_MIN_FRAUD_TXN_COUNT = 1
PROXY_MIN_FRAUD_CONCENTRATION = 0.5


def compute_cluster_fraud_labels(
    clusters_df: pd.DataFrame, entity_fraud_count: pd.Series, entity_txn_count: pd.Series
) -> pd.DataFrame:
    """entity_fraud_count / entity_txn_count: pseudo_entity_id -> counts,
    aggregated over the DEVELOPMENT split only when this is called for
    threshold selection (caller's responsibility to pass dev-restricted
    aggregates — see select_proxy_params_on_dev)."""
    rows = []
    for _, cluster in clusters_df.iterrows():
        members = list(cluster["members"])
        fraud_txns = entity_fraud_count.reindex(members).fillna(0).sum()
        total_txns = entity_txn_count.reindex(members).fillna(0).sum()
        concentration = fraud_txns / total_txns if total_txns > 0 else 0.0
        rows.append(
            {
                "cluster_id": cluster["cluster_id"],
                "fraud_txn_count": fraud_txns,
                "total_txn_count": total_txns,
                "fraud_concentration": concentration,
            }
        )
    return pd.DataFrame(rows)


def label_relevant(
    cluster_fraud_labels: pd.DataFrame,
    min_fraud_txn_count: int = PROXY_MIN_FRAUD_TXN_COUNT,
    min_concentration: float = PROXY_MIN_FRAUD_CONCENTRATION,
) -> pd.Series:
    return (cluster_fraud_labels["fraud_txn_count"] >= min_fraud_txn_count) | (
        cluster_fraud_labels["fraud_concentration"] >= min_concentration
    )


def precision_at_k(ranked_cluster_ids: list[str], relevant_set: set[str], k: int) -> float:
    top_k = ranked_cluster_ids[:k]
    if not top_k:
        return 0.0
    return sum(1 for c in top_k if c in relevant_set) / len(top_k)


def recall_at_k(ranked_cluster_ids: list[str], relevant_set: set[str], k: int) -> float:
    if not relevant_set:
        return 0.0
    top_k = set(ranked_cluster_ids[:k])
    return len(top_k & relevant_set) / len(relevant_set)


def lift_over_baseline(system_precision_at_k: float, baseline_precision_at_k: float) -> float:
    if baseline_precision_at_k == 0:
        return float("inf") if system_precision_at_k > 0 else 1.0
    return system_precision_at_k / baseline_precision_at_k


def run_layer_b1(
    scored_hybrid: pd.DataFrame,  # has cluster_id, cluster_score, members
    baseline_a_ranking: list[str],  # cluster_ids ranked by total txn value
    baseline_b_ranking: list[str],  # cluster_ids ranked by max member risk
    baseline_c_ranking: list[str],  # cluster_ids ranked by structural score
    cluster_fraud_labels: pd.DataFrame,
    k: int = 20,
    min_fraud_txn_count: int = PROXY_MIN_FRAUD_TXN_COUNT,
    min_concentration: float = PROXY_MIN_FRAUD_CONCENTRATION,
) -> dict:
    relevant_mask = label_relevant(cluster_fraud_labels, min_fraud_txn_count, min_concentration)
    relevant_set = set(cluster_fraud_labels.loc[relevant_mask, "cluster_id"])

    hybrid_ranking = list(scored_hybrid.sort_values("cluster_score", ascending=False)["cluster_id"])

    results = {}
    for name, ranking in [
        ("hybrid_final", hybrid_ranking),
        ("baseline_a_value", baseline_a_ranking),
        ("baseline_b_max_risk", baseline_b_ranking),
        ("baseline_c_structural", baseline_c_ranking),
    ]:
        p = precision_at_k(ranking, relevant_set, k)
        r = recall_at_k(ranking, relevant_set, k)
        results[name] = {"precision_at_k": p, "recall_at_k": r, "k": k}

    results["hybrid_final"]["lift_over_baseline_a"] = lift_over_baseline(
        results["hybrid_final"]["precision_at_k"], results["baseline_a_value"]["precision_at_k"]
    )
    results["hybrid_final"]["lift_over_baseline_b"] = lift_over_baseline(
        results["hybrid_final"]["precision_at_k"], results["baseline_b_max_risk"]["precision_at_k"]
    )
    results["_meta"] = {
        "num_relevant_clusters": len(relevant_set),
        "num_total_clusters": len(cluster_fraud_labels),
        "proxy_min_fraud_txn_count": min_fraud_txn_count,
        "proxy_min_concentration": min_concentration,
        "label_type": "Layer B1 (derived proxy from transaction-level labels) — NOT ring ground truth",
    }
    return results


def select_proxy_and_thresholds_on_dev(
    clusters_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    entity_fraud_count_dev: pd.Series,
    entity_txn_count_dev: pd.Series,
    candidate_min_members: list[int],
    candidate_min_concentration: list[float],
) -> dict:
    """
    Sweep MIN_CLUSTER_MEMBERS and the fraud-concentration proxy threshold on
    the DEVELOPMENT split only (DATA_STRATEGY.md Section 6), picking the
    combination that yields the best precision@K on the dev-derived proxy
    labels. This is the actual threshold-selection step Day 3 requires —
    everything upstream used Day-1/2 prototype defaults.
    """
    from graph.scoring import apply_minimum_evidence_filter

    best = None
    all_results = []
    for min_members in candidate_min_members:
        filtered = apply_minimum_evidence_filter(clusters_df, edges_df, min_members=min_members)
        if filtered.empty:
            continue
        labels = compute_cluster_fraud_labels(filtered, entity_fraud_count_dev, entity_txn_count_dev)
        for min_conc in candidate_min_concentration:
            relevant_mask = label_relevant(labels, min_fraud_txn_count=1, min_concentration=min_conc)
            relevant_set = set(labels.loc[relevant_mask, "cluster_id"])
            # rank candidate: use cluster size + fraud concentration as a cheap
            # dev-only proxy ranking signal purely for threshold SELECTION
            # (not the final hybrid score, which needs the full pipeline)
            ranking = list(labels.sort_values("fraud_concentration", ascending=False)["cluster_id"])
            p_at_20 = precision_at_k(ranking, relevant_set, min(20, len(ranking)))
            record = {
                "min_members": min_members,
                "min_concentration": min_conc,
                "num_clusters": len(filtered),
                "num_relevant": len(relevant_set),
                "precision_at_20": p_at_20,
            }
            all_results.append(record)
            if best is None or p_at_20 > best["precision_at_20"]:
                best = record
    return {"best": best, "all_sweep_results": all_results}

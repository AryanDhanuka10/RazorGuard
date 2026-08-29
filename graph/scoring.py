"""
graph/scoring.py

Normalized hybrid cluster score (PROJECT_MASTER_PLAN.md Section 7):

cluster_score = w1*relationship_concentration + w2*transaction_risk
              + w3*temporal_coordination + w4*structural_anomaly + w5*exposure
  where w1+...+w5 = 1, every component in [0,1].

Weights below are documented INITIAL ASSUMPTIONS (Section 7: "documented as
initial assumptions with a sensitivity check"), not a tuned result.

SCOPE NOTE (BUILD_CONTRACT.md Section 15 — resolve ambiguity transparently,
don't silently invent canon): the plan's train/dev/test leakage rule is
transaction-level, but pseudo-entities and qualified-graph clusters are built
by pooling transactions across the whole timeline (a cluster's members can
have transactions in more than one split). There is no cluster-level
train/dev/test split defined anywhere in the canonical docs. This
implementation fits every normalization bound (min/max for exposure,
temporal, structural components) across the FULL set of extracted clusters,
since no narrower "dev-only clusters" subset is definable from what's
specified — documented here explicitly rather than silently claimed to
satisfy a leakage rule that doesn't actually have a cluster-level definition
to satisfy. The leakage rule that IS unambiguous and IS honored end-to-end:
`MIN_CLUSTER_MEMBERS`/`MIN_INDEPENDENT_RELATIONSHIPS`/edge-qualification
threshold selection uses only the Layer B1 proxy (graph/evaluation.py),
never `scenarios_test.yaml`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = {
    "relationship_concentration": 0.2,
    "transaction_risk": 0.2,
    "temporal_coordination": 0.2,
    "structural_anomaly": 0.2,
    "exposure": 0.2,
}
assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9

MIN_CLUSTER_MEMBERS_DEFAULT = 2
MIN_INDEPENDENT_RELATIONSHIPS_DEFAULT = 1  # at least 1 qualified edge type present


def _minmax(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi - lo < 1e-12:
        return pd.Series(0.0, index=s.index)
    return (s - lo) / (hi - lo)


def compute_relationship_concentration(clusters_df: pd.DataFrame, qualified_edges: pd.DataFrame) -> pd.Series:
    """
    Fraction of a cluster's internal shared-identifier instances that connect
    3+ members. For each cluster, look at every qualified internal edge's
    signal_types; group members by identifier co-membership isn't directly
    available post-qualification (identifier_value isn't kept on qualify_edges'
    output), so this uses a documented approximation: for each signal_type
    present on 2+ internal edges, if those edges collectively touch 3+ distinct
    members, count that signal_type instance as "concentrated". Ratio of
    concentrated signal-type instances to total distinct signal-type instances
    present in the cluster. Already in [0,1] by construction — no scaling.
    """
    scores = []
    for _, cluster in clusters_df.iterrows():
        members = set(cluster["members"])
        internal = qualified_edges[
            qualified_edges["entity_a"].isin(members) & qualified_edges["entity_b"].isin(members)
        ]
        if internal.empty:
            scores.append(0.0)
            continue
        signal_type_members: dict[str, set] = {}
        for _, row in internal.iterrows():
            for st in row["signal_types"]:
                signal_type_members.setdefault(st, set()).update([row["entity_a"], row["entity_b"]])
        total_types = len(signal_type_members)
        concentrated_types = sum(1 for m in signal_type_members.values() if len(m) >= 3)
        scores.append(concentrated_types / total_types if total_types else 0.0)
    return pd.Series(scores, index=clusters_df.index)


def compute_mean_transaction_risk(
    clusters_df: pd.DataFrame, entity_risk_scores: pd.Series
) -> pd.Series:
    """entity_risk_scores: pseudo_entity_id -> mean XGBoost predicted probability
    across that entity's transactions. Already in [0,1] — no scaling needed."""
    return clusters_df["members"].apply(
        lambda members: entity_risk_scores.reindex(list(members)).dropna().mean()
        if len(entity_risk_scores.reindex(list(members)).dropna())
        else 0.0
    )


def compute_temporal_coordination(clusters_df: pd.DataFrame, entity_dt: pd.Series) -> pd.Series:
    """inverse of activity time-spread within the cluster, min-max scaled to
    [0,1] across all clusters (see module-level SCOPE NOTE)."""
    spreads = clusters_df["members"].apply(
        lambda members: (
            entity_dt.reindex(list(members)).dropna().max() - entity_dt.reindex(list(members)).dropna().min()
        )
        if len(entity_dt.reindex(list(members)).dropna()) > 1
        else 0.0
    )
    inverse_spread = 1.0 / (1.0 + spreads)
    return _minmax(inverse_spread)


def compute_structural_anomaly(
    clusters_df: pd.DataFrame, qualified_edges: pd.DataFrame, total_entity_count: int
) -> pd.Series:
    """cluster density relative to background graph density, min-max scaled."""
    background_possible_pairs = total_entity_count * (total_entity_count - 1) / 2
    background_density = len(qualified_edges) / background_possible_pairs if background_possible_pairs else 0.0

    def density_ratio(members):
        n = len(members)
        possible = n * (n - 1) / 2
        if possible == 0 or background_density == 0:
            return 0.0
        internal = qualified_edges[
            qualified_edges["entity_a"].isin(members) & qualified_edges["entity_b"].isin(members)
        ]
        cluster_density = len(internal) / possible
        return cluster_density / background_density

    raw = clusters_df["members"].apply(density_ratio)
    return _minmax(raw)


def compute_exposure(clusters_df: pd.DataFrame, entity_total_amt: pd.Series) -> pd.Series:
    """log1p(cluster_transaction_value), min-max scaled to [0,1]."""
    totals = clusters_df["members"].apply(lambda members: entity_total_amt.reindex(list(members)).dropna().sum())
    log_totals = np.log1p(totals)
    return _minmax(log_totals)


def compute_hybrid_cluster_score(
    clusters_df: pd.DataFrame,
    qualified_edges: pd.DataFrame,
    entity_risk_scores: pd.Series,
    entity_dt: pd.Series,
    entity_total_amt: pd.Series,
    total_entity_count: int,
    weights: dict = None,
) -> pd.DataFrame:
    weights = weights or DEFAULT_WEIGHTS
    assert abs(sum(weights.values()) - 1.0) < 1e-6, "weights must sum to 1"

    out = clusters_df.copy()
    out["relationship_concentration"] = compute_relationship_concentration(clusters_df, qualified_edges)
    out["transaction_risk"] = compute_mean_transaction_risk(clusters_df, entity_risk_scores)
    out["temporal_coordination"] = compute_temporal_coordination(clusters_df, entity_dt)
    out["structural_anomaly"] = compute_structural_anomaly(clusters_df, qualified_edges, total_entity_count)
    out["exposure"] = compute_exposure(clusters_df, entity_total_amt)

    for col in ["relationship_concentration", "transaction_risk", "temporal_coordination", "structural_anomaly", "exposure"]:
        assert out[col].between(0, 1).all(), f"{col} must be in [0,1]"

    out["cluster_score"] = (
        weights["relationship_concentration"] * out["relationship_concentration"]
        + weights["transaction_risk"] * out["transaction_risk"]
        + weights["temporal_coordination"] * out["temporal_coordination"]
        + weights["structural_anomaly"] * out["structural_anomaly"]
        + weights["exposure"] * out["exposure"]
    )
    return out.sort_values("cluster_score", ascending=False).reset_index(drop=True)


def apply_minimum_evidence_filter(
    clusters_df: pd.DataFrame,
    qualified_edges: pd.DataFrame,
    min_members: int = MIN_CLUSTER_MEMBERS_DEFAULT,
    min_independent_relationships: int = MIN_INDEPENDENT_RELATIONSHIPS_DEFAULT,
) -> pd.DataFrame:
    """MIN_CLUSTER_MEMBERS / MIN_INDEPENDENT_RELATIONSHIPS — configurable
    parameters, not hardcoded (Section 7). Selected properly via the Layer B1
    proxy in graph/evaluation.py; these are just the mechanism."""

    def independent_relationship_count(members):
        internal = qualified_edges[
            qualified_edges["entity_a"].isin(members) & qualified_edges["entity_b"].isin(members)
        ]
        all_types = set()
        for types in internal["signal_types"]:
            all_types.update(types)
        return len(all_types)

    filtered = clusters_df[clusters_df["size"] >= min_members].copy()
    filtered["independent_relationship_count"] = filtered["members"].apply(independent_relationship_count)
    return filtered[filtered["independent_relationship_count"] >= min_independent_relationships]


def weight_sensitivity_check(
    scored_clusters: pd.DataFrame, base_weights: dict, perturbation: float = 0.3, top_k: int = 20
) -> dict:
    """Rerank top-K clusters under +/-perturbation weight changes on each
    weight in turn (renormalized to sum to 1), report how much the top-K set
    changes vs. the base ranking (Section 7's required sensitivity check)."""
    base_top_k = set(scored_clusters.head(top_k)["cluster_id"])
    results = {}
    for key in base_weights:
        for direction, sign in (("up", 1), ("down", -1)):
            perturbed = dict(base_weights)
            perturbed[key] = max(0.0, perturbed[key] * (1 + sign * perturbation))
            total = sum(perturbed.values())
            perturbed = {k: v / total for k, v in perturbed.items()}

            recombined = (
                perturbed["relationship_concentration"] * scored_clusters["relationship_concentration"]
                + perturbed["transaction_risk"] * scored_clusters["transaction_risk"]
                + perturbed["temporal_coordination"] * scored_clusters["temporal_coordination"]
                + perturbed["structural_anomaly"] * scored_clusters["structural_anomaly"]
                + perturbed["exposure"] * scored_clusters["exposure"]
            )
            reranked = scored_clusters.assign(_score=recombined).sort_values("_score", ascending=False)
            new_top_k = set(reranked.head(top_k)["cluster_id"])
            overlap = len(base_top_k & new_top_k) / top_k
            results[f"{key}_{direction}"] = {"top_k_overlap_fraction": overlap}
    return results

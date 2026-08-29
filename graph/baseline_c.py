"""
graph/baseline_c.py

Baseline C (EVALUATION_PLAN.md Section 2): rank candidate clusters by a
graph-structural score ALONE — concentration/temporal/structural-anomaly
signal derived purely from the qualified graph and connected components.
Deliberately excludes transaction risk (ml/ Layer A output) so it can be
compared fairly against the final hybrid score, which does use risk.

Unnormalized at this stage (DAILY_BUILD_PLAN.md Day 2: "unnormalized is fine
at this stage") — normalization is Day 3's job (graph/scoring.py).
"""
from __future__ import annotations

import pandas as pd


def compute_baseline_c_structural_score(
    clusters_df: pd.DataFrame, qualified_edges: pd.DataFrame, entity_representative_view: pd.DataFrame
) -> pd.DataFrame:
    """
    For each cluster: size, edge density (actual qualified edges / possible
    pairs within the cluster), mean edge_evidence_score among internal edges,
    and temporal spread (max-min transaction_dt among members) — combined as
    an UNNORMALIZED sum (Day 2 baseline; real normalization is Day 3).
    """
    dt_lookup = entity_representative_view.set_index("pseudo_entity_id")["transaction_dt"]

    rows = []
    for _, cluster in clusters_df.iterrows():
        members = set(cluster["members"])
        n = len(members)
        possible_pairs = n * (n - 1) / 2

        internal_edges = qualified_edges[
            qualified_edges["entity_a"].isin(members) & qualified_edges["entity_b"].isin(members)
        ]
        density = len(internal_edges) / possible_pairs if possible_pairs > 0 else 0.0
        mean_evidence = internal_edges["edge_evidence_score"].mean() if len(internal_edges) else 0.0

        member_dts = dt_lookup.reindex(list(members)).dropna()
        temporal_spread = (member_dts.max() - member_dts.min()) if len(member_dts) > 1 else 0.0

        # unnormalized structural score: bigger, denser, higher-evidence,
        # temporally-tighter clusters score higher (division by (1+spread) as
        # a crude temporal-tightness term — a real normalization comes Day 3)
        structural_score = n * density * (mean_evidence if mean_evidence else 0.01) / (1 + temporal_spread / 86400)

        rows.append(
            {
                "cluster_id": cluster["cluster_id"],
                "size": n,
                "edge_density": density,
                "mean_edge_evidence": mean_evidence,
                "temporal_spread_days": temporal_spread / 86400,
                "baseline_c_score": structural_score,
            }
        )
    return pd.DataFrame(rows).sort_values("baseline_c_score", ascending=False).reset_index(drop=True)

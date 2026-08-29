"""
graph/cluster.py

Candidate cluster extraction via connected components — run ONLY on the
qualified graph (graph/edges.py output), never on raw signals.

This is deterministic connected components. It is NOT community detection.
No Louvain/Leiden/label-propagation/GNN is implemented in this project
(BUILD_CONTRACT.md Section 7 / PROJECT_MASTER_PLAN.md Section 4).
"""
from __future__ import annotations

import networkx as nx
import pandas as pd


def build_qualified_graph(qualified_edges: pd.DataFrame) -> nx.Graph:
    g = nx.Graph()
    for _, row in qualified_edges.iterrows():
        g.add_edge(
            row["entity_a"],
            row["entity_b"],
            weight=row["edge_evidence_score"],
            signal_types=row["signal_types"],
        )
    return g


def extract_clusters(g: nx.Graph, min_members: int = 2) -> list[set[str]]:
    """Plain connected components, filtered by a minimum member count.
    `min_members` is a tunable parameter (MIN_CLUSTER_MEMBERS,
    PROJECT_MASTER_PLAN.md Section 7), not a hardcoded truth."""
    return [c for c in nx.connected_components(g) if len(c) >= min_members]


def clusters_to_dataframe(clusters: list[set[str]]) -> pd.DataFrame:
    rows = []
    for i, members in enumerate(clusters):
        rows.append({"cluster_id": f"cluster_{i:05d}", "members": sorted(members), "size": len(members)})
    return pd.DataFrame(rows)

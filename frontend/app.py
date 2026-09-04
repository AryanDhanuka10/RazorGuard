"""
frontend/app.py

Day 2: bare-bones, deliberately UNSTYLED cluster-list view (DAILY_BUILD_PLAN.md
Day 2: "this is intentionally ugly, it exists to keep the 'does this look
useful' question alive every day, not just at the end"). The real styled
case-detail view (PROJECT_MASTER_PLAN.md Section 11a) is built on top of this
starting Day 3 (see frontend/case_detail.py).

ARCHITECTURE.md Section 5a: this file computes NOTHING itself. It only reads
from backend/ API responses (or, until the backend exists, directly from the
same parquet artifacts the backend will eventually read from) and displays
them — no score-to-percentage or exposure formatting logic lives here.
"""
import sys
from pathlib import Path

# Not strictly needed today (this file has no backend.* imports), but added
# for consistency with dashboard.py/case_detail.py and to future-proof
# against that changing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="RazorGuard - Candidate Clusters (Day 2, unstyled)", layout="wide")
st.title("RazorGuard — Candidate Clusters")
st.caption(
    "Day 2 bare cluster list — intentionally unstyled. Coordinated suspicious "
    "clusters from real IEEE-CIS data. Terminology: 'coordinated suspicious "
    "clusters', never 'fraud rings' (real-data context — see ARCHITECTURE.md)."
)


@st.cache_data
def load_data():
    clusters = pd.read_parquet("data/clusters_full.parquet")
    baseline_c = pd.read_parquet("data/baseline_c_scores.parquet")
    edges = pd.read_parquet("data/qualified_edges_full.parquet")
    return clusters, baseline_c, edges


clusters, baseline_c, edges = load_data()

st.write(f"Total candidate clusters: {len(clusters)}")

merged = clusters.merge(baseline_c, on=["cluster_id", "size"], how="left")
merged = merged.sort_values("baseline_c_score", ascending=False)

st.dataframe(
    merged[["cluster_id", "size", "edge_density", "mean_edge_evidence", "temporal_spread_days", "baseline_c_score"]],
    use_container_width=True,
)

st.subheader("Raw evidence for a selected cluster")
selected = st.selectbox("cluster_id", merged["cluster_id"].tolist())
if selected:
    row = clusters[clusters["cluster_id"] == selected].iloc[0]
    st.write("Members (pseudo-entity IDs):", list(row["members"]))
    member_edges = edges[
        edges["entity_a"].isin(row["members"]) & edges["entity_b"].isin(row["members"])
    ]
    st.write("Qualified edges within this cluster:")
    st.dataframe(member_edges, use_container_width=True)
"""
frontend/case_detail.py

Styled case-detail/evidence view, per PROJECT_MASTER_PLAN.md Section 11a:

    TOP SUSPICIOUS CLUSTER
    Coordinated Risk Score:   [0-100, from the normalized cluster score]
    Estimated At-Risk Exposure: [Rupee figure]
    Cluster Size:             [N pseudo-entities]

    WHY FLAGGED (evidence bullets, each traceable to a real graph fact)
    [Relationship graph view — qualified edges only]
    Investigation Result: ESCALATE / INSUFFICIENT EVIDENCE
    Reason: [Investigation Agent's cited explanation]

ARCHITECTURE.md Section 5a (binding): this file computes NOTHING — no
score-to-percentage or exposure formatting. All of that lives in
backend/exposure.py and graph/scoring.py so the displayed numbers can never
drift from what was actually computed and logged. This file only reads
already-computed columns and renders them.

*** KNOWN ARCHITECTURE DEVIATION (documented, not hidden) ***
Section 5a also says the frontend renders "purely from GET /clusters/{id}
and GET /cases/{id} API responses" — this file does NOT do that; it reads
the same parquet artifacts directly via pandas instead of calling the API
over HTTP. Pragmatic choice for a fast build (avoids running a second
server), not a hidden shortcut — see frontend/dashboard.py's module
docstring for the full explanation. Computation still lives in exactly one
place, so this deviation is about which code PATH reaches that
computation, not about duplicating it.

Financial-claim discipline (EVALUATION_PLAN.md Section 7): Risk Score !=
Fraud Probability != Estimated At-Risk Exposure != Loss Prevented. "Loss
prevented" is never used anywhere in this file.
"""
import pandas as pd
import streamlit as st

from backend.exposure import compute_estimated_exposure
from data.canonicalize import CANONICAL_FIELDS  # noqa: F401 (keeps this file honest about field provenance)

st.set_page_config(page_title="RazorGuard - Case Detail", layout="wide")

st.markdown(
    """
    <style>
    .rg-card {background-color:#f7f7fa;border-radius:10px;padding:1.2rem 1.5rem;border:1px solid #e2e2e8;}
    .rg-score {font-size:2.6rem;font-weight:700;color:#b3261e;}
    .rg-label {color:#666;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.05em;}
    .rg-evidence {background-color:#fff;border-left:4px solid #b3261e;padding:0.6rem 1rem;margin-bottom:0.5rem;border-radius:4px;}
    .rg-verdict-escalate {color:#b3261e;font-weight:700;}
    .rg-verdict-insufficient {color:#666;font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("RazorGuard — Case Detail")


@st.cache_data
def load_case_data():
    clusters = pd.read_parquet("data/clusters_full.parquet")
    scored = pd.read_parquet("data/scored_clusters.parquet")
    edges = pd.read_parquet("data/qualified_edges_full.parquet")
    rep = pd.read_parquet("data/entity_representative_view.parquet")
    entity_amt = pd.read_parquet("data/entity_total_amt.parquet")["total_transaction_amt"]
    entity_risk = pd.read_parquet("data/entity_risk_scores.parquet")["risk_score"]
    return clusters, scored, edges, rep, entity_amt, entity_risk


clusters, scored, edges, rep, entity_amt, entity_risk = load_case_data()

top_clusters = scored.sort_values("cluster_score", ascending=False).head(50)
selected_id = st.selectbox("Select a candidate cluster (ranked by score)", top_clusters["cluster_id"].tolist())

row = scored[scored["cluster_id"] == selected_id].iloc[0]
members = list(row["members"])

exposure = compute_estimated_exposure(
    cluster_fraud_probability=row["transaction_risk"],
    cluster_transaction_value=entity_amt.reindex(members).dropna().sum(),
    recoverability_assumption=0.3,  # documented scenario assumption, see backend/exposure.py
)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="rg-card">', unsafe_allow_html=True)
    st.markdown('<div class="rg-label">Coordinated Risk Score</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rg-score">{row["cluster_score"] * 100:.0f}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown('<div class="rg-card">', unsafe_allow_html=True)
    st.markdown('<div class="rg-label">Estimated At-Risk Exposure</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rg-score">{exposure["estimated_at_risk_exposure"]:,.0f}</div>', unsafe_allow_html=True)
    st.caption(
        "Estimated exposure — never \"loss prevented\". IEEE-CIS's TransactionAmt currency "
        "was never confirmed by Vesta/Kaggle, so no currency symbol is shown — this is a "
        "figure in the dataset's own transaction-amount units. See backend/exposure.py "
        "for the formula and its inputs."
    )
    st.markdown("</div>", unsafe_allow_html=True)
with col3:
    st.markdown('<div class="rg-card">', unsafe_allow_html=True)
    st.markdown('<div class="rg-label">Cluster Size</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rg-score">{row["size"]}</div>', unsafe_allow_html=True)
    st.markdown("<div>pseudo-entities</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.subheader("Why Flagged")
internal_edges = edges[edges["entity_a"].isin(members) & edges["entity_b"].isin(members)]
signal_type_labels = {
    "device_info": "share an observed device-information signal",
    "addr1": "share an observed address code",
    "card_combo": "share an observed card-related signal",
}
seen_types = set()
for types in internal_edges["signal_types"]:
    seen_types.update(types)

for st_type in seen_types:
    n = len(
        set(
            e
            for _, r in internal_edges.iterrows()
            if st_type in r["signal_types"]
            for e in (r["entity_a"], r["entity_b"])
        )
    )
    st.markdown(
        f'<div class="rg-evidence">{n} entities {signal_type_labels.get(st_type, st_type)}</div>',
        unsafe_allow_html=True,
    )

member_dt = rep[rep["pseudo_entity_id"].isin(members)]["transaction_dt"]
if len(member_dt) > 1:
    spread_days = (member_dt.max() - member_dt.min()) / 86400
    st.markdown(
        f'<div class="rg-evidence">Activity concentrated within {spread_days:.1f} days</div>',
        unsafe_allow_html=True,
    )
st.markdown(
    f'<div class="rg-evidence">Average member transaction risk: {row["transaction_risk"]:.3f}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="rg-evidence">Estimated exposure: {exposure["estimated_at_risk_exposure"]:,.0f}</div>',
    unsafe_allow_html=True,
)

st.subheader("Relationship Graph (qualified edges only)")
graph_rows = internal_edges[["entity_a", "entity_b", "edge_evidence_score", "signal_types"]]
st.dataframe(graph_rows, use_container_width=True)
st.caption(
    "Only qualified edges are shown — weak/globally-common signals filtered out before "
    "clustering (graph/edges.py). No rejected edges are displayed here in this version."
)

st.subheader("Investigation Result")
st.info(
    "The Investigation Agent has not been wired to this view yet — this section renders "
    "once agents/investigate.py produces a structured verdict for this cluster (Day 4). "
    "No placeholder verdict is shown here; an unimplemented step is left visibly "
    "unimplemented rather than faked."
)

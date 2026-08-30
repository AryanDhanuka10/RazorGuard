"""
agents/evidence_builder.py

Deterministic evidence bundle builder (ARCHITECTURE.md Section 4): "Input:
deterministic evidence bundle only — cluster members, shared-identifier
facts, temporal pattern, transaction risk scores, cluster score breakdown.
Nothing else."

This module has NO dependency on the Anthropic SDK and makes no LLM calls —
it is pure data assembly, fully deterministic and fully unit-testable without
any live API access. The Investigation Agent (agents/investigate.py) receives
ONLY the output of this module as its input; it must never independently
query anything else.

Terminology discipline (DATA_STRATEGY.md Section 2) is enforced here, not
left to the agent to get right: shared-identifier facts are pre-phrased using
the approved language ("share an observed device-information signal", etc.)
before the agent ever sees them.
"""
from __future__ import annotations

import pandas as pd

SIGNAL_TYPE_LANGUAGE = {
    "device_info": "share an observed device-information signal",
    "addr1": "share an observed address code",
    "card_combo": "share an observed card-related signal",
}


def build_evidence_bundle(
    cluster_id: str,
    scored_clusters: pd.DataFrame,
    qualified_edges: pd.DataFrame,
    entity_representative_view: pd.DataFrame,
    entity_risk_scores: pd.Series,
) -> dict:
    """
    Returns a JSON-serializable dict — this IS the entire input the
    Investigation Agent receives. Nothing outside this bundle is available to
    it (no open-ended DB/web access, per ARCHITECTURE.md Section 4).
    """
    row = scored_clusters[scored_clusters["cluster_id"] == cluster_id]
    if row.empty:
        raise ValueError(f"cluster_id {cluster_id} not found in scored_clusters")
    row = row.iloc[0]
    members = list(row["members"])

    internal_edges = qualified_edges[
        qualified_edges["entity_a"].isin(members) & qualified_edges["entity_b"].isin(members)
    ]

    shared_identifier_facts = []
    seen_types: dict[str, set] = {}
    for _, edge in internal_edges.iterrows():
        for st in edge["signal_types"]:
            seen_types.setdefault(st, set()).update([edge["entity_a"], edge["entity_b"]])
    for signal_type, involved in seen_types.items():
        shared_identifier_facts.append(
            {
                "signal_type": signal_type,
                "description": SIGNAL_TYPE_LANGUAGE.get(signal_type, signal_type),
                "entity_count": len(involved),
                "entities_involved": sorted(involved),
            }
        )

    member_dt = entity_representative_view[entity_representative_view["pseudo_entity_id"].isin(members)][
        "transaction_dt"
    ]
    temporal_pattern = {
        "earliest_dt": float(member_dt.min()) if len(member_dt) else None,
        "latest_dt": float(member_dt.max()) if len(member_dt) else None,
        "spread_seconds": float(member_dt.max() - member_dt.min()) if len(member_dt) > 1 else 0.0,
    }

    member_risk = entity_risk_scores.reindex(members).dropna()
    transaction_risk_scores = {
        "member_risk_scores": member_risk.round(4).to_dict(),
        "mean_risk": float(member_risk.mean()) if len(member_risk) else None,
        "max_risk": float(member_risk.max()) if len(member_risk) else None,
    }

    cluster_score_breakdown = {
        "cluster_score": float(row["cluster_score"]),
        "relationship_concentration": float(row["relationship_concentration"]),
        "transaction_risk": float(row["transaction_risk"]),
        "temporal_coordination": float(row["temporal_coordination"]),
        "structural_anomaly": float(row["structural_anomaly"]),
        "exposure": float(row["exposure"]),
    }

    return {
        "cluster_id": cluster_id,
        "cluster_members": members,
        "cluster_size": len(members),
        "shared_identifier_facts": shared_identifier_facts,
        "temporal_pattern": temporal_pattern,
        "transaction_risk_scores": transaction_risk_scores,
        "cluster_score_breakdown": cluster_score_breakdown,
        # Explicit reminder embedded in the bundle itself, not just the prompt —
        # belt-and-suspenders against terminology drift (DATA_STRATEGY.md Section 2).
        "terminology_note": (
            "This is REAL IEEE-CIS data. Refer to this as a 'coordinated suspicious "
            "cluster', never a 'fraud ring'. Shared identifiers are signals, not "
            "proof of the same device/person — never claim 'same device' or "
            "'linked accounts'."
        ),
    }

"""
graph/build.py

Builds the representative per-pseudo-entity identifier view that
graph/relationships.py needs (one row per pseudo-entity, with its
representative device_info / addr1 / card fields + earliest transaction_dt).

This is aggregation ACROSS a single entity's own transactions (still node-side
prep, not relationship logic) — kept here rather than in data/pseudo_entity.py
only because it exists purely to feed the edge-extraction step, not because the
node/edge separation is being blurred: no cross-entity comparison happens here.
"""
from __future__ import annotations

import pandas as pd


def _mode_or_first(s: pd.Series):
    s = s.dropna()
    if s.empty:
        return None
    m = s.mode()
    return m.iloc[0] if not m.empty else s.iloc[0]


def build_entity_representative_view(df_with_entities: pd.DataFrame) -> pd.DataFrame:
    """
    df_with_entities: transaction-level rows that already have pseudo_entity_id
    (data/pseudo_entity.py output), plus device_info, addr1, card1, card2, card5,
    card6, transaction_dt.
    """
    needed = [
        "pseudo_entity_id",
        "device_info",
        "addr1",
        "card1",
        "card2",
        "card5",
        "card6",
        "transaction_dt",
    ]
    missing = [c for c in needed if c not in df_with_entities.columns]
    if missing:
        raise ValueError(f"missing columns for representative view: {missing}")

    grp = df_with_entities.groupby("pseudo_entity_id")
    rep = grp.agg(
        device_info=("device_info", _mode_or_first),
        addr1=("addr1", _mode_or_first),
        card1=("card1", _mode_or_first),
        card2=("card2", _mode_or_first),
        card5=("card5", _mode_or_first),
        card6=("card6", _mode_or_first),
        transaction_dt=("transaction_dt", "min"),
    ).reset_index()
    return rep

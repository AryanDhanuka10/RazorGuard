"""
data/pseudo_entity.py

Pseudo-entity resolution: transactions -> pseudo-entities -> graph NODES.

This is a documented, widely-used Kaggle-community heuristic for IEEE-CIS
(PROJECT_MASTER_PLAN.md Section 3 / DATA_STRATEGY.md Section 2), not an
official Vesta label and not a verified real-world identity link.

HARD SEPARATION (BUILD_CONTRACT.md Section 6): this module groups transactions
that likely belong to the same recurring payer into one node. It does NOT
determine whether two different pseudo-entities are related to each other —
that is relationship-signal extraction + edge qualification, entirely in
graph/relationships.py and graph/edges.py. Nothing in this file writes an edge.
"""
from __future__ import annotations

import hashlib

import pandas as pd

PSEUDO_ENTITY_KEY_FIELDS = ["card1", "card2", "addr1", "d1"]
PSEUDO_ENTITY_HEURISTIC_VERSION = "v1-card1_card2_addr1_d1"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def resolve_pseudo_entities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a `pseudo_entity_id` column to the canonical transaction table.

    Returns a new DataFrame; does not mutate the input.

    Implementation note (see FAILURE_LOG.md "Row-wise fingerprinting OOM/killed
    at full dataset scale"): the original version called a Python hashing
    function via `df.apply(..., axis=1)`, which builds a per-row Series object
    for all 590K rows and was killed by the sandbox's OOM killer. This version
    builds the composite key as a single vectorized string-concatenation
    column, deduplicates it with `pd.factorize` to get a compact integer code
    per unique key (no per-row Python hashing at all), and only computes the
    human-legible SHA256 fingerprint once per *unique* key (tens of thousands,
    not hundreds of thousands) as a final, cheap step.
    """
    for f in PSEUDO_ENTITY_KEY_FIELDS:
        if f not in df.columns:
            raise ValueError(
                f"pseudo-entity resolution requires column '{f}' — "
                f"run canonicalization first (data/canonicalize.py)"
            )
    out = df.copy()

    # Vectorized composite key: NaN becomes the literal "NA" per field (not
    # dropped), so "missing addr1" is part of the key rather than collapsing
    # every addr1-missing row together under a shorter key.
    key_parts = [out[f].astype("string").fillna("NA") for f in PSEUDO_ENTITY_KEY_FIELDS]
    composite_key = key_parts[0]
    for part in key_parts[1:]:
        composite_key = composite_key + "|" + part

    # pd.factorize is a single vectorized pass -> integer code per unique key.
    codes, uniques = pd.factorize(composite_key, sort=False)

    # Hash only the unique keys (small), then map codes -> hash via a lookup array.
    unique_hashes = [_hash_key(k) for k in uniques]
    out["pseudo_entity_id"] = pd.Series(codes, index=out.index).map(
        dict(enumerate(unique_hashes))
    )
    out["pseudo_entity_heuristic_version"] = PSEUDO_ENTITY_HEURISTIC_VERSION
    return out


def build_entity_table(df_with_entities: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse transactions into one row per pseudo-entity (a graph NODE):
    member count, total/mean transaction value, mean risk placeholder columns
    are added later once the risk model exists (ml/), fraud-label concentration
    (only meaningful for Layer B1's proxy, computed here since it's a direct
    aggregate of is_fraud, not a modeling step).
    """
    grp = df_with_entities.groupby("pseudo_entity_id")
    entities = grp.agg(
        transaction_count=("transaction_id", "count"),
        total_transaction_amt=("transaction_amt", "sum"),
        mean_transaction_amt=("transaction_amt", "mean"),
        fraud_label_count=("is_fraud", "sum"),
        fraud_label_rate=("is_fraud", "mean"),
        first_seen_dt=("transaction_dt", "min"),
        last_seen_dt=("transaction_dt", "max"),
    ).reset_index()
    return entities

"""
graph/edges.py

Edge evidence scoring + edge qualification (PROJECT_MASTER_PLAN.md Section 4a).

edge_evidence_score = f(identifier_rarity, independent_signal_count, temporal_proximity)

Only signals whose score clears EDGE_QUALIFICATION_THRESHOLD become qualified
graph edges. Connected components (graph/cluster.py) runs ONLY on the output
of this module — never on raw signals. This is the deterministic fix for
bridge-chaining through weak/globally-common shared identifiers.

All thresholds here are tunable parameters, not hardcoded truths — they must be
selected on the development split only (DATA_STRATEGY.md Section 6), never on
test data. Defaults below are Day-1 prototype starting points for the sanity
check; final values get swept properly on Day 3 (DAILY_BUILD_PLAN.md).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# --- Day-1 prototype defaults (NOT final — swept properly on Day 3 against
# the Layer B1 proxy on the development split, per EVALUATION_PLAN.md Section 2) ---
EDGE_QUALIFICATION_THRESHOLD = 0.3
TEMPORAL_WINDOW_SECONDS = 6 * 3600  # 6 hours: signals within this window score highest
# NOTE: the previous population-percentage-based rarity cap
# (IDENTIFIER_RARITY_GLOBAL_COMMON_CAP) was removed — see FAILURE_LOG.md
# "Bridge-chaining from percentage-based identifier rarity". Rarity is now
# computed from absolute global entity counts (compute_global_identifier_counts /
# compute_identifier_rarity below).


def compute_global_identifier_counts(full_representative_view: pd.DataFrame) -> pd.DataFrame:
    """
    Global (population-level) count of DISTINCT entities holding each
    (signal_type, identifier_value), computed once from the FULL entity
    representative view — never from whatever subset happens to be scored.

    Must be built from graph/build.py's representative view (which already has
    card_combo computed the same way relationships.py does), see
    FAILURE_LOG.md "Bridge-chaining from percentage-based identifier rarity".
    """
    from graph.relationships import build_card_combo_key

    df = full_representative_view.copy()
    df["card_combo"] = df.apply(build_card_combo_key, axis=1)

    counts = []
    for signal_type, col in (("device_info", "device_info"), ("addr1", "addr1"), ("card_combo", "card_combo")):
        c = df.dropna(subset=[col]).groupby(col)["pseudo_entity_id"].nunique()
        c = c.rename("entity_count").reset_index().rename(columns={col: "identifier_value"})
        c["identifier_value"] = c["identifier_value"].astype(str)
        c["signal_type"] = signal_type
        counts.append(c)
    return pd.concat(counts, ignore_index=True)


def compute_identifier_rarity(
    signals: pd.DataFrame, global_counts: pd.DataFrame
) -> pd.Series:
    """
    rarity = 1 / (1 + log1p(global_entity_count_sharing_this_value)).

    Deliberately NOT a population-percentage measure. FAILURE_LOG.md "Bridge-
    chaining from percentage-based identifier rarity" found that addr1 has only
    332 distinct values across 248,038 entities (~747 entities/value on
    average) — no population-percentage cap can distinguish "common" from
    "rare" for a field with that little cardinality, because almost every
    value looks like a small percentage of a large population even when it is,
    in absolute terms, held by tens of thousands of entities. Using the
    absolute count directly (log-scaled so a handful of very common values
    don't need an arbitrary cutoff) fixes this: a value shared by 2 entities
    scores ~0.48; a value shared by 16,000+ entities scores ~0.09.
    """
    merged = signals.merge(
        global_counts, on=["signal_type", "identifier_value"], how="left"
    )
    counts = merged["entity_count"].fillna(2)  # unseen in global table -> conservative floor
    rarity = 1.0 / (1.0 + np.log1p(counts))
    return pd.Series(rarity.values, index=signals.index)


def compute_temporal_proximity(signals: pd.DataFrame) -> pd.Series:
    """1.0 at zero gap, decaying linearly to 0 at TEMPORAL_WINDOW_SECONDS and beyond."""
    gap = signals["temporal_gap_seconds"].fillna(TEMPORAL_WINDOW_SECONDS)
    prox = 1 - (gap / TEMPORAL_WINDOW_SECONDS)
    return prox.clip(lower=0, upper=1)


def compute_independent_signal_count(signals: pd.DataFrame) -> pd.DataFrame:
    """
    Per entity-pair, how many DISTINCT signal_types connect them (device+card is
    stronger evidence than device alone). Returns a pair-level table merged back
    onto the original signal rows.
    """
    pair_key = signals[["entity_a", "entity_b"]].copy()
    pair_key["pair"] = list(zip(signals["entity_a"], signals["entity_b"]))
    counts = signals.groupby(["entity_a", "entity_b"])["signal_type"].transform("nunique")
    return counts


def score_edges(signals: pd.DataFrame, global_counts: pd.DataFrame) -> pd.DataFrame:
    """
    Input: raw signal rows (graph/relationships.py output, as a DataFrame), and
    the GLOBAL identifier-count table (compute_global_identifier_counts, built
    once from the full entity representative view — see FAILURE_LOG.md "Bridge-
    chaining from percentage-based identifier rarity" for why this must be
    global rather than computed from whatever subset is being scored).
    Output: same rows + rarity, temporal_proximity, independent_signal_count,
    and edge_evidence_score columns. One row per (entity_a, entity_b, signal_type)
    — aggregation to one score per PAIR happens in qualify_edges().
    """
    if signals.empty:
        out = signals.copy()
        for c in ["identifier_rarity", "temporal_proximity", "independent_signal_count", "edge_evidence_score"]:
            out[c] = pd.Series(dtype=float)
        return out

    out = signals.copy()
    out["identifier_rarity"] = compute_identifier_rarity(out, global_counts)
    out["temporal_proximity"] = compute_temporal_proximity(out)
    out["independent_signal_count"] = compute_independent_signal_count(out)

    # independent_signal_count is normalized against a soft cap of 3 distinct
    # signal types (device, addr1, card_combo is the max in this project).
    norm_independent = (out["independent_signal_count"] / 3.0).clip(upper=1.0)

    out["edge_evidence_score"] = (
        0.5 * out["identifier_rarity"] + 0.3 * norm_independent + 0.2 * out["temporal_proximity"]
    )
    return out


SINGLE_SIGNAL_HIGH_RARITY_BAR = 0.4  # a lone signal type must be quite rare on its own to qualify alone


def qualify_edges(
    scored_signals: pd.DataFrame, threshold: float = EDGE_QUALIFICATION_THRESHOLD
) -> pd.DataFrame:
    """
    Collapse to one row per (entity_a, entity_b) pair, taking the MAX
    edge_evidence_score and the corresponding max identifier_rarity across
    that pair's signal types, then keep only pairs that BOTH clear `threshold`
    AND satisfy a minimum-independent-evidence rule:
      - 2+ distinct signal types corroborate the pair, OR
      - a single signal type is present but its own identifier_rarity clears
        SINGLE_SIGNAL_HIGH_RARITY_BAR (i.e. it's a genuinely rare shared value,
        not just "close in time").

    This second rule is an explicit IMPLEMENTATION DECISION, not a canonical
    requirement pulled from the plan docs (BUILD_CONTRACT.md Section 15 —
    ambiguities must be resolved transparently, not silently invented as
    canon). It exists because a single weak, common signal (e.g. a shared
    address-region code) combined only with temporal proximity was clearing
    the base threshold on its own during the Day 1 sanity check — see
    FAILURE_LOG.md "Bridge-chaining from percentage-based identifier rarity".
    Requiring either independent corroboration or a genuinely rare single
    signal is a reasonable interim tightening; the real threshold and this
    rule's necessity get re-examined on Day 3 against the Layer B1 proxy.
    """
    if scored_signals.empty:
        return pd.DataFrame(columns=["entity_a", "entity_b", "edge_evidence_score", "signal_types"])

    pair_grp = scored_signals.groupby(["entity_a", "entity_b"])
    pairs = pair_grp.agg(
        edge_evidence_score=("edge_evidence_score", "max"),
        max_identifier_rarity=("identifier_rarity", "max"),
        signal_types=("signal_type", lambda s: sorted(set(s))),
    ).reset_index()

    clears_score = pairs["edge_evidence_score"] >= threshold
    has_independent_corroboration = pairs["signal_types"].map(len) >= 2
    single_signal_but_rare = pairs["max_identifier_rarity"] >= SINGLE_SIGNAL_HIGH_RARITY_BAR

    qualified = pairs[clears_score & (has_independent_corroboration | single_signal_but_rare)].copy()
    return qualified.sort_values("edge_evidence_score", ascending=False).reset_index(drop=True)

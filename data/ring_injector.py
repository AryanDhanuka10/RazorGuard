"""
data/ring_injector.py

Seeded ring injector (DATA_STRATEGY.md Section 5): IEEE-CIS has no ring-level
ground truth, so this generates labeled ring scenarios on top of REAL
IEEE-CIS records (real transactions, synthetic *grouping* pattern only)
strictly to fill that one gap for Layer B2.

CONFIGURATION ISOLATION (hard rule, DATA_STRATEGY.md Section 5 /
BUILD_CONTRACT.md Section 10):
  configs/scenarios_dev.yaml   <- used freely Days 1-4: building/debugging/tuning
  configs/scenarios_test.yaml  <- opened exactly once, Day 5, never before

This module is config-agnostic — it takes a scenario spec dict and doesn't
care which file it came from. THE CALLER is responsible for isolation: no
code path in this repository reads `scenarios_test.yaml` before Day 5 (see
scripts/day5_final_evaluation.py, the only file permitted to reference it).
"""
from __future__ import annotations

import random

import pandas as pd


def inject_ring_scenario(
    entity_representative_view: pd.DataFrame,
    scenario: dict,
    seed: int,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Pick `scenario['ring_size']` real, otherwise-unrelated pseudo-entities and
    synthetically overwrite their device_info (or addr1/card fields per
    `scenario['shared_signal']`) to a shared synthetic value, within a
    temporal window per `scenario['temporal_spread_hours']`. Returns the
    modified representative view (copy) plus the list of pseudo_entity_ids
    that are now the injected ring's real ground-truth members.

    This is the ONLY source of cluster/ring-level ground truth in the whole
    project — real IEEE-CIS has none (EVALUATION_PLAN.md Section 3).
    """
    rng = random.Random(seed)
    df = entity_representative_view.copy()

    eligible = df["pseudo_entity_id"].tolist()
    ring_members = rng.sample(eligible, k=scenario["ring_size"])

    if not ring_members:
        # zero-size ring (negative control) -> return input completely
        # unmodified, including dtypes, so it's a true no-op.
        return df, ring_members

    # transaction_dt must be able to hold the injected float offset (base_dt +
    # a uniform random offset) even if the source column is integer-typed —
    # otherwise pandas raises TypeError assigning a float into an int64 column.
    df["transaction_dt"] = df["transaction_dt"].astype("float64")

    synthetic_value = f"SYNTH-{scenario['shared_signal']}-{seed}"
    base_dt = df["transaction_dt"].median()
    spread_seconds = scenario.get("temporal_spread_hours", 1) * 3600

    # 'card_combo' is NOT a real column on the representative view — it is
    # computed on the fly, downstream, by graph/relationships.py from
    # card1+card2+card5+card6 (see build_card_combo_key). Writing a synthetic
    # value into a literal 'card_combo' column here would do nothing useful:
    # extract_all_raw_signals() recomputes card_combo from those four raw
    # fields and would silently overwrite/ignore the injected value (see
    # FAILURE_LOG.md "Ring injector card_combo scenarios silently no-ops").
    # For this signal type, inject into the four underlying fields directly,
    # giving all ring members an identical (card1, card2, card5, card6) tuple
    # — which is exactly what a real 'shared card-related combination' is.
    if scenario["shared_signal"] == "card_combo":
        card_fields = ["card1", "card2", "card5", "card6"]
        for f in card_fields:
            if df[f].dtype != object:
                df[f] = df[f].astype(object)
        synthetic_card_values = {f: f"{synthetic_value}-{f}" for f in card_fields}
    else:
        target_col = scenario["shared_signal"]
        # The target column (device_info, addr1) may be numeric in the source
        # data (e.g. addr1 is float-typed) but the synthetic value is always a
        # string — casting the column to object dtype first avoids a pandas
        # TypeError ("Invalid value ... for dtype 'float64'") when assigning a
        # string into a numeric column.
        if df[target_col].dtype != object:
            df[target_col] = df[target_col].astype(object)

    for i, entity_id in enumerate(ring_members):
        offset = rng.uniform(0, spread_seconds)
        mask = df["pseudo_entity_id"] == entity_id
        if scenario["shared_signal"] == "card_combo":
            for f, v in synthetic_card_values.items():
                df.loc[mask, f] = v
        else:
            df.loc[mask, target_col] = synthetic_value
        df.loc[mask, "transaction_dt"] = base_dt + offset

    return df, ring_members


def inject_all_scenarios(
    entity_representative_view: pd.DataFrame, scenarios: list[dict], base_seed: int
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """
    Apply every scenario in the config sequentially (each scenario's ring is
    independent — later scenarios don't overwrite earlier ones' injected
    values, since each picks from `eligible` fresh each time; a genuinely
    unlucky overlap is possible but is treated as an acceptable, documented
    property of random sampling rather than something this function
    special-cases away).
    """
    df = entity_representative_view.copy()
    ground_truth: dict[str, list[str]] = {}
    for i, scenario in enumerate(scenarios):
        df, members = inject_ring_scenario(df, scenario, seed=base_seed + i)
        ground_truth[scenario["scenario_id"]] = members
    return df, ground_truth

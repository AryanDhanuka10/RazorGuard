"""
graph/relationships.py

Raw inter-entity relationship signal extraction BETWEEN DISTINCT pseudo-entities.

HARD SEPARATION (BUILD_CONTRACT.md Section 6 / ARCHITECTURE.md Section 1):
pseudo-entities already exist as graph NODES before this module runs
(data/pseudo_entity.py). This module never groups transactions into entities —
it only asks, for pairs of DIFFERENT entities, whether they share an identifier
value, and if so, treats that as one RAW relationship signal. Whether a raw
signal is strong enough to become a qualified graph EDGE is a separate step
(graph/edges.py) — nothing here writes to a "qualified graph".

Terminology discipline (DATA_STRATEGY.md Section 2 / BUILD_CONTRACT.md Section 4.1):
a shared identifier is described as "a shared observed device-information
signal" / "a shared address code" / "a shared card-related signal" — never as
proof of the same device, same person, or linked accounts.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import pandas as pd

# Signal types this project extracts. Each corresponds to one raw shared
# identifier kind between two distinct pseudo-entities.
SIGNAL_TYPES = ("device_info", "addr1", "card_combo")


@dataclass(frozen=True)
class RawSignal:
    entity_a: str
    entity_b: str
    signal_type: str
    identifier_value: str
    entity_a_dt: float
    entity_b_dt: float

    @property
    def temporal_gap_seconds(self) -> float:
        return abs(self.entity_a_dt - self.entity_b_dt)


def _entity_identifier_table(entities_df: pd.DataFrame, id_col: str) -> pd.DataFrame:
    """One row per (pseudo_entity_id, identifier_value, representative_dt),
    dropping nulls — a null identifier is never treated as a shared value."""
    sub = entities_df[["pseudo_entity_id", id_col, "transaction_dt"]].dropna(subset=[id_col])
    # representative_dt: earliest occurrence of this identifier for this entity
    sub = sub.groupby(["pseudo_entity_id", id_col], as_index=False)["transaction_dt"].min()
    return sub


def extract_signals_for_identifier(
    df: pd.DataFrame, id_col: str, signal_type: str, max_group_size: int = 500
) -> list[RawSignal]:
    """
    For a single identifier column (e.g. device_info), find all pairs of
    DISTINCT pseudo-entities that share a value, and emit one RawSignal per pair.

    `max_group_size` guards against a single globally-common identifier value
    (e.g. a null-like sentinel, or an extremely common device string) producing
    a combinatorial explosion of pairs — such groups are skipped entirely here
    and rely on edge qualification's identifier-rarity scoring downstream to
    down-weight anything that *does* get through at a smaller scale. This cap
    is a computational safeguard, not the qualification logic itself.
    """
    table = _entity_identifier_table(df, id_col)
    signals: list[RawSignal] = []
    for value, group in table.groupby(id_col):
        entities = group["pseudo_entity_id"].tolist()
        dts = dict(zip(group["pseudo_entity_id"], group["transaction_dt"]))
        n = len(entities)
        if n < 2 or n > max_group_size:
            continue
        for a, b in combinations(sorted(entities), 2):
            signals.append(
                RawSignal(
                    entity_a=a,
                    entity_b=b,
                    signal_type=signal_type,
                    identifier_value=str(value),
                    entity_a_dt=dts[a],
                    entity_b_dt=dts[b],
                )
            )
    return signals


def build_card_combo_key(row: pd.Series) -> str | None:
    """card-related combination signal: card1+card2+card5+card6 together,
    per PROJECT_MASTER_PLAN.md Section 4 ('shared card-related combination').
    Any missing component -> no combo signal for this row (never fill with a
    placeholder that could accidentally collide across rows)."""
    fields = ["card1", "card2", "card5", "card6"]
    if any(pd.isna(row.get(f)) for f in fields):
        return None
    return "|".join(str(row[f]) for f in fields)


def extract_all_raw_signals(
    entities_df: pd.DataFrame, max_group_size: int = 500
) -> list[RawSignal]:
    """
    entities_df: one row per pseudo-entity's REPRESENTATIVE transaction-level
    identifier values (device_info, addr1, card fields) plus transaction_dt and
    pseudo_entity_id. Caller is responsible for building this representative
    view (see graph/build.py) — this function does not do node aggregation.
    """
    df = entities_df.copy()
    df["card_combo"] = df.apply(build_card_combo_key, axis=1)

    signals: list[RawSignal] = []
    signals += extract_signals_for_identifier(df, "device_info", "device_info", max_group_size)
    signals += extract_signals_for_identifier(df, "addr1", "addr1", max_group_size)
    signals += extract_signals_for_identifier(df, "card_combo", "card_combo", max_group_size)
    return signals


def signals_to_dataframe(signals: list[RawSignal]) -> pd.DataFrame:
    if not signals:
        return pd.DataFrame(
            columns=[
                "entity_a",
                "entity_b",
                "signal_type",
                "identifier_value",
                "temporal_gap_seconds",
            ]
        )
    return pd.DataFrame(
        {
            "entity_a": [s.entity_a for s in signals],
            "entity_b": [s.entity_b for s in signals],
            "signal_type": [s.signal_type for s in signals],
            "identifier_value": [s.identifier_value for s in signals],
            "temporal_gap_seconds": [s.temporal_gap_seconds for s in signals],
        }
    )

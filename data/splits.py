"""
data/splits.py

Time-based train/development/test split (EVALUATION_PLAN.md Section 1 /
DATA_STRATEGY.md Section 6). NEVER a random split — IEEE-CIS transactions from
the same pseudo-entity are temporally clustered, so a random split would leak
that entity's other transactions across train/test.

Split boundaries are chosen as transaction_dt quantiles (a fixed, documented
choice — not tuned against any metric), producing three contiguous time
windows: train (earliest), development (middle), test (latest, held out).
"""
from __future__ import annotations

import pandas as pd

TRAIN_FRACTION = 0.70
DEV_FRACTION = 0.15
# remaining 0.15 is TEST


def compute_split_boundaries(df: pd.DataFrame, dt_col: str = "transaction_dt") -> tuple[float, float]:
    sorted_dt = df[dt_col].sort_values()
    n = len(sorted_dt)
    train_end = sorted_dt.iloc[int(n * TRAIN_FRACTION)]
    dev_end = sorted_dt.iloc[int(n * (TRAIN_FRACTION + DEV_FRACTION))]
    return train_end, dev_end


def assign_split(df: pd.DataFrame, dt_col: str = "transaction_dt") -> pd.Series:
    train_end, dev_end = compute_split_boundaries(df, dt_col)
    split = pd.Series("test", index=df.index)
    split[df[dt_col] <= train_end] = "train"
    split[(df[dt_col] > train_end) & (df[dt_col] <= dev_end)] = "dev"
    return split

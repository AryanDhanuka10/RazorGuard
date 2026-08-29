"""
data/canonicalize.py

Deterministic canonicalization of raw IEEE-CIS fields into a typed feature table.
Field semantics follow DATA_STRATEGY.md Section 2 exactly — no field is given a
stronger meaning than the table there allows (e.g. card1-6 are "card-related
attributes", never "credit card number"; addr1/addr2 are "address-region codes",
never "home address").

This module owns NODE-relevant canonicalization only. It does not construct
pseudo-entities (see data/pseudo_entity.py) and does not construct relationship
edges (see graph/relationships.py) — kept separate per BUILD_CONTRACT.md Section 6.
"""
from __future__ import annotations

import pandas as pd

# Columns this project actually uses, with their honest semantic label.
# Anything not listed here is passed through untouched (e.g. the V-columns),
# never re-labeled with an invented meaning.
CANONICAL_FIELDS = {
    "TransactionID": "transaction_id",
    "isFraud": "is_fraud",
    "TransactionDT": "transaction_dt",  # seconds offset from an unspecified reference point, per Kaggle docs
    "TransactionAmt": "transaction_amt",
    "ProductCD": "product_cd",
    "card1": "card1",
    "card2": "card2",
    "card3": "card3",
    "card4": "card4",
    "card5": "card5",
    "card6": "card6",
    "addr1": "addr1",  # address-region code, NOT a home address
    "addr2": "addr2",  # address-region code, NOT a home address
    "P_emaildomain": "p_emaildomain",
    "R_emaildomain": "r_emaildomain",
    "D1": "d1",  # time-delta field used in pseudo-entity heuristic
}
# NOTE: DeviceType/DeviceInfo are intentionally NOT listed here. They exist only
# in the identity table (see IDENTITY_CANONICAL_FIELDS below), and a transaction
# has one only if it has a matching identity row. Declaring them here too used to
# create an all-NaN placeholder in the transaction table that silently won the
# merge over the real identity values — see FAILURE_LOG.md "Device info silently
# null after merge".

REQUIRED_RAW_COLUMNS = list(CANONICAL_FIELDS.keys())


def load_raw_transactions(path: str, nrows: int | None = None) -> pd.DataFrame:
    """Load the raw IEEE-CIS transaction CSV. No transformation here."""
    return pd.read_csv(path, nrows=nrows)


def load_raw_identity(path: str, nrows: int | None = None) -> pd.DataFrame:
    """Load the raw IEEE-CIS identity CSV. No transformation here."""
    return pd.read_csv(path, nrows=nrows)


def canonicalize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produce the canonical feature table for transactions.

    - Renames fields to their canonical, semantically-honest names.
    - Leaves values untouched (no imputation/scaling here — that belongs to
      whichever downstream stage needs it, fit only on train/dev, per
      DATA_STRATEGY.md Section 6 leakage rule).
    - Missing optional columns (e.g. D1 can be absent in some exports) are
      created as all-NaN rather than raising, since D1 sparsity is itself a
      documented real-data characteristic (see FAILURE_LOG.md if this occurs).
    """
    missing = [c for c in REQUIRED_RAW_COLUMNS if c not in df.columns]
    if missing:
        missing_block = pd.DataFrame({c: pd.NA for c in missing}, index=df.index)
        df = pd.concat([df, missing_block], axis=1)

    known = df[REQUIRED_RAW_COLUMNS].rename(columns=CANONICAL_FIELDS)
    passthrough_cols = [c for c in df.columns if c not in REQUIRED_RAW_COLUMNS]
    out = pd.concat([known, df[passthrough_cols]], axis=1).copy()

    return out


IDENTITY_CANONICAL_FIELDS = {
    "TransactionID": "transaction_id",
    "DeviceType": "device_type",
    "DeviceInfo": "device_info",
}


def canonicalize_identity(df: pd.DataFrame) -> pd.DataFrame:
    """Identity table: pass through as-is, keyed on TransactionID. id_01-id_38 stay
    documented as 'undisclosed anonymized identity/behavioral features' — never
    given an invented interpretation.

    DeviceType/DeviceInfo are explicitly renamed to their canonical lowercase
    names here (not left as raw Kaggle names) — see FAILURE_LOG.md "Device info
    silently null after merge" for why this matters: canonicalize_transactions()
    creates all-NaN placeholders for DeviceType/DeviceInfo (since the raw
    transaction table doesn't have them), so if this table's copies keep their
    raw names instead of the canonical ones, the merge silently keeps two
    device columns — the real one under the raw name, and an all-NaN one under
    the canonical name that everything downstream actually reads from.
    """
    out = df.rename(columns=IDENTITY_CANONICAL_FIELDS).copy()
    return out


def merge_transaction_identity(txn: pd.DataFrame, identity: pd.DataFrame) -> pd.DataFrame:
    """Left join on transaction_id. Most transactions have no identity row —
    that's an expected, documented characteristic of IEEE-CIS, not a bug."""
    return txn.merge(identity, on="transaction_id", how="left", suffixes=("", "_identity"))

import pandas as pd
from data.canonicalize import (
    canonicalize_transactions,
    canonicalize_identity,
    merge_transaction_identity,
)


def _fake_txn():
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "isFraud": [0, 1, 0],
            "TransactionDT": [100, 200, 300],
            "TransactionAmt": [10.0, 20.0, 30.0],
            "ProductCD": ["W", "W", "C"],
            "card1": [111, 222, 333],
            "card2": [1.0, None, 3.0],
            "card3": [150.0, 150.0, 150.0],
            "card4": ["visa", "visa", "mastercard"],
            "card5": [100.0, 100.0, 100.0],
            "card6": ["debit", "debit", "credit"],
            "addr1": [200.0, 200.0, None],
            "addr2": [87.0, 87.0, 87.0],
            "P_emaildomain": ["a.com", "b.com", None],
            "R_emaildomain": [None, None, None],
            "D1": [0.0, 5.0, None],
            "extra_v_col": [1, 2, 3],
        }
    )


def _fake_identity():
    return pd.DataFrame(
        {
            "TransactionID": [1, 3],
            "DeviceType": ["mobile", "desktop"],
            "DeviceInfo": ["iOS Device", "Windows"],
            "id_01": [0.1, 0.2],
        }
    )


def test_canonicalize_transactions_renames_and_preserves_passthrough():
    out = canonicalize_transactions(_fake_txn())
    assert "transaction_id" in out.columns
    assert "is_fraud" in out.columns
    assert "addr1" in out.columns
    # passthrough column must survive untouched
    assert "extra_v_col" in out.columns
    # device fields must NOT appear here — they only come from identity (regression
    # test for the "Device info silently null after merge" failure)
    assert "device_info" not in out.columns
    assert "device_type" not in out.columns


def test_canonicalize_identity_renames_device_fields():
    out = canonicalize_identity(_fake_identity())
    assert "device_type" in out.columns
    assert "device_info" in out.columns
    assert "DeviceType" not in out.columns
    assert "DeviceInfo" not in out.columns


def test_merge_preserves_real_device_values_not_nulled():
    ctxn = canonicalize_transactions(_fake_txn())
    cident = canonicalize_identity(_fake_identity())
    merged = merge_transaction_identity(ctxn, cident)

    # transaction_id 1 and 3 have identity rows with real device info
    row1 = merged.loc[merged["transaction_id"] == 1].iloc[0]
    row3 = merged.loc[merged["transaction_id"] == 3].iloc[0]
    row2 = merged.loc[merged["transaction_id"] == 2].iloc[0]

    assert row1["device_info"] == "iOS Device"
    assert row3["device_info"] == "Windows"
    # transaction_id 2 has no identity row at all -> expected null, not a bug
    assert pd.isna(row2["device_info"])

    # exactly one device_info / device_type column each — no duplicate raw-named columns
    assert list(merged.columns).count("device_info") == 1
    assert list(merged.columns).count("device_type") == 1
    assert "DeviceInfo" not in merged.columns
    assert "DeviceType" not in merged.columns


def test_missing_optional_column_created_as_null_not_raised():
    txn = _fake_txn().drop(columns=["D1"])
    out = canonicalize_transactions(txn)
    assert "d1" in out.columns
    assert out["d1"].isna().all()

import numpy as np
import pandas as pd

from ml.risk_model import select_feature_columns, prepare_xy, evaluate, train_xgboost


def test_select_feature_columns_only_numeric_prefixed():
    df = pd.DataFrame(
        {
            "V1": [1.0, 2.0],
            "C2": [3.0, 4.0],
            "D3": [5.0, 6.0],
            "ProductCD": ["W", "C"],  # non-numeric, must be excluded
            "transaction_amt": [10.0, 20.0],
            "is_fraud": [0, 1],
        }
    )
    cols = select_feature_columns(df)
    assert set(cols) == {"V1", "C2", "D3", "transaction_amt"}
    assert "ProductCD" not in cols
    assert "is_fraud" not in cols


def test_prepare_xy_fills_missing_with_sentinel():
    df = pd.DataFrame({"V1": [1.0, None], "is_fraud": [0, 1]})
    X, y = prepare_xy(df, ["V1"])
    assert X[1, 0] == -999.0
    assert list(y) == [0, 1]


def test_evaluate_perfect_predictions():
    y_true = np.array([0, 0, 1, 1])
    y_pred_proba = np.array([0.01, 0.02, 0.9, 0.95])
    m = evaluate(y_true, y_pred_proba)
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["false_positive_rate"] == 0.0


def test_train_xgboost_runs_on_tiny_fixture_and_produces_probabilities():
    rng = np.random.RandomState(0)
    X = rng.rand(200, 5)
    y = (X[:, 0] > 0.8).astype(int)  # deterministic separable signal
    model = train_xgboost(X, y)
    proba = model.predict_proba(X)[:, 1]
    assert proba.shape == (200,)
    assert ((proba >= 0) & (proba <= 1)).all()

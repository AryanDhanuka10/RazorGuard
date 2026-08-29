"""
ml/risk_model.py

Layer A: transaction-level classification (EVALUATION_PLAN.md Section 1).
XGBoost vs. a simple logistic-regression baseline on raw features, using the
time-based train/test split (data/splits.py) — never random, to avoid leaking
a pseudo-entity's transactions across train and test.

This module owns modeling only (ARCHITECTURE.md Section 2's component
boundary table: ml/ owns "XGBoost training/inference (Layer A)", nothing about
graph construction or decisions).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

FEATURE_PREFIXES = ("V", "C", "D")  # V*, C*, D* numeric risk features from IEEE-CIS
EXTRA_NUMERIC_FEATURES = ["transaction_amt"]


def select_feature_columns(df: pd.DataFrame) -> list[str]:
    cols = [c for c in df.columns if c.startswith(FEATURE_PREFIXES) and df[c].dtype != object]
    cols += [c for c in EXTRA_NUMERIC_FEATURES if c in df.columns]
    return sorted(set(cols))


def prepare_xy(df: pd.DataFrame, feature_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    X = df[feature_cols].fillna(-999.0).values  # fixed sentinel, fit on nothing (no leakage risk)
    y = df["is_fraud"].values
    return X, y


def train_xgboost(X_train, y_train) -> xgb.XGBClassifier:
    # class imbalance handled via scale_pos_weight, computed from TRAIN split only
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos_weight = n_neg / max(n_pos, 1)

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model


def train_logistic_baseline(X_train, y_train) -> tuple[LogisticRegression, StandardScaler]:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)  # fit on TRAIN only
    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(X_scaled, y_train)
    return model, scaler


def evaluate(y_true, y_pred_proba, threshold: float = 0.5) -> dict:
    y_pred = (y_pred_proba >= threshold).astype(int)
    tn_fp_mask = y_true == 0
    fp = ((y_pred == 1) & tn_fp_mask).sum()
    fp_rate = fp / max(tn_fp_mask.sum(), 1)
    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "pr_auc": average_precision_score(y_true, y_pred_proba),
        "roc_auc": roc_auc_score(y_true, y_pred_proba),
        "false_positive_rate": fp_rate,
    }

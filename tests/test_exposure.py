import pytest

from backend.exposure import compute_estimated_exposure


def test_exposure_formula_is_the_product_of_three_inputs():
    result = compute_estimated_exposure(0.5, 1000.0, 0.3)
    assert result["estimated_at_risk_exposure"] == pytest.approx(150.0)
    assert result["model_risk_proxy"] == 0.5
    assert result["cluster_transaction_value"] == 1000.0
    assert result["recoverability_assumption"] == 0.3


def test_result_never_calls_the_input_a_calibrated_fraud_probability():
    """Regression test for the transaction_risk -> cluster_fraud_probability
    semantic bug (external review): the result dict must not expose a key
    named cluster_fraud_probability, and the label must not claim this is a
    calibrated probability."""
    result = compute_estimated_exposure(0.5, 1000.0, 0.3)
    assert "cluster_fraud_probability" not in result
    assert "model_risk_proxy" in result
    assert "not a calibrated cluster fraud probability" in result["label"].lower()


def test_rejects_probability_out_of_range():
    with pytest.raises(ValueError):
        compute_estimated_exposure(1.5, 1000.0, 0.3)


def test_rejects_negative_transaction_value():
    with pytest.raises(ValueError):
        compute_estimated_exposure(0.5, -10.0, 0.3)


def test_never_labeled_as_loss_prevented():
    """The label may mention 'loss prevented' only to explicitly disclaim it
    (EVALUATION_PLAN.md Section 7: 'never claimed anywhere'). The real check
    is that 'loss prevented' never appears as an unqualified claim — i.e. the
    word 'never' or 'not' must appear alongside it."""
    result = compute_estimated_exposure(0.5, 1000.0, 0.3)
    label = result["label"].lower()
    if "loss prevented" in label:
        assert "never" in label or "not" in label
    assert "estimate" in label

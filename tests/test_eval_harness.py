from agents.eval_harness import (
    ReviewedCase,
    compute_schema_validity_rate,
    compute_evidence_faithfulness,
    compute_insufficient_evidence_correctness,
    run_full_evaluation,
)


def _valid_case(case_id, verdict="escalate", grounded=None, weak=None):
    response = {
        "verdict": verdict,
        "confidence": 0.7,
        "claims": [{"claim": "x", "cited_field": "shared_identifier_facts"}] if verdict == "escalate" else [],
    }
    return ReviewedCase(
        case_id=case_id, evidence_bundle={}, raw_agent_response=response,
        claims_grounded=grounded, is_actually_weak_case=weak,
    )


def _malformed_case(case_id):
    return ReviewedCase(case_id=case_id, evidence_bundle={}, raw_agent_response={"verdict": "maybe"})


def test_schema_validity_rate_mixed_valid_and_invalid():
    cases = [_valid_case("c1"), _valid_case("c2"), _malformed_case("c3")]
    result = compute_schema_validity_rate(cases)
    assert result["schema_validity_rate"] == 2 / 3
    assert len(result["invalid_cases"]) == 1
    assert result["invalid_cases"][0]["case_id"] == "c3"


def test_evidence_faithfulness_with_no_reviewed_cases_returns_none():
    cases = [_valid_case("c1")]  # claims_grounded not set
    result = compute_evidence_faithfulness(cases)
    assert result["evidence_faithfulness_rate"] is None


def test_evidence_faithfulness_computed_correctly():
    cases = [
        _valid_case("c1", grounded=[True, True]),
        _valid_case("c2", grounded=[True, False]),
    ]
    result = compute_evidence_faithfulness(cases)
    assert result["evidence_faithfulness_rate"] == 3 / 4
    assert result["unsupported_claim_rate"] == 1 / 4


def test_insufficient_evidence_correctness():
    cases = [
        _valid_case("c1", verdict="insufficient_evidence", weak=True),  # correct
        _valid_case("c2", verdict="escalate", weak=True),  # incorrect — should've said insufficient
        _valid_case("c3", verdict="escalate", weak=False),  # not a weak case, excluded
    ]
    result = compute_insufficient_evidence_correctness(cases)
    assert result["insufficient_evidence_correctness"] == 0.5
    assert result["num_weak_cases"] == 2


def test_run_full_evaluation_flags_case_count_target():
    cases = [_valid_case(f"c{i}") for i in range(5)]
    result = run_full_evaluation(cases)
    assert result["num_cases"] == 5
    assert result["meets_20_to_30_case_target"] is False

    cases_25 = [_valid_case(f"c{i}") for i in range(25)]
    result_25 = run_full_evaluation(cases_25)
    assert result_25["meets_20_to_30_case_target"] is True

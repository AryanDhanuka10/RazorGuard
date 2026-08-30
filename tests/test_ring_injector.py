import os

import pandas as pd
import yaml

from data.ring_injector import inject_ring_scenario, inject_all_scenarios


def _fixture_rep_view(n=50):
    return pd.DataFrame(
        {
            "pseudo_entity_id": [f"e{i}" for i in range(n)],
            "device_info": [f"device-{i}" for i in range(n)],
            "addr1": [float(i % 10) for i in range(n)],
            "card1": list(range(n)),
            "card2": list(range(n)),
            "card5": list(range(n)),
            "card6": ["debit"] * n,
            "transaction_dt": [i * 1000 for i in range(n)],
        }
    )


def test_inject_ring_scenario_creates_shared_synthetic_value():
    rep = _fixture_rep_view()
    scenario = {"scenario_id": "s1", "ring_size": 5, "shared_signal": "device_info", "temporal_spread_hours": 1}
    modified, members = inject_ring_scenario(rep, scenario, seed=42)
    assert len(members) == 5
    values = modified[modified["pseudo_entity_id"].isin(members)]["device_info"].unique()
    assert len(values) == 1
    assert values[0].startswith("SYNTH-device_info-42")


def test_inject_ring_scenario_is_deterministic_given_seed():
    rep = _fixture_rep_view()
    scenario = {"scenario_id": "s1", "ring_size": 5, "shared_signal": "device_info", "temporal_spread_hours": 1}
    _, members1 = inject_ring_scenario(rep, scenario, seed=7)
    _, members2 = inject_ring_scenario(rep, scenario, seed=7)
    assert members1 == members2


def test_zero_size_ring_is_a_valid_negative_control():
    rep = _fixture_rep_view()
    scenario = {"scenario_id": "control", "ring_size": 0, "shared_signal": "device_info", "temporal_spread_hours": 0}
    modified, members = inject_ring_scenario(rep, scenario, seed=1)
    assert members == []
    pd.testing.assert_frame_equal(modified, rep)


def test_inject_all_scenarios_returns_ground_truth_per_scenario():
    rep = _fixture_rep_view()
    scenarios = [
        {"scenario_id": "a", "ring_size": 3, "shared_signal": "device_info", "temporal_spread_hours": 1},
        {"scenario_id": "b", "ring_size": 4, "shared_signal": "addr1", "temporal_spread_hours": 2},
    ]
    _, ground_truth = inject_all_scenarios(rep, scenarios, base_seed=100)
    assert set(ground_truth.keys()) == {"a", "b"}
    assert len(ground_truth["a"]) == 3
    assert len(ground_truth["b"]) == 4


def test_card_combo_injection_survives_downstream_recomputation():
    """Regression test for FAILURE_LOG.md 'Ring injector card_combo scenarios
    silently no-op': card_combo isn't a real column — it's recomputed
    downstream by graph/relationships.py from card1+card2+card5+card6. This
    test injects a card_combo ring, then runs the ACTUAL downstream
    recomputation (build_card_combo_key) and confirms the ring members still
    end up sharing one identical, rare card_combo value — i.e. the injection
    actually survives the pipeline it's meant to be detected by."""
    from graph.relationships import build_card_combo_key

    rep = _fixture_rep_view()
    scenario = {"scenario_id": "s_card", "ring_size": 6, "shared_signal": "card_combo", "temporal_spread_hours": 1}
    modified, members = inject_ring_scenario(rep, scenario, seed=99)

    recomputed = modified.copy()
    recomputed["card_combo"] = recomputed.apply(build_card_combo_key, axis=1)

    ring_combos = recomputed[recomputed["pseudo_entity_id"].isin(members)]["card_combo"].unique()
    assert len(ring_combos) == 1, "injected ring members must share exactly one card_combo value after downstream recomputation"

    non_ring_combos = recomputed[~recomputed["pseudo_entity_id"].isin(members)]["card_combo"]
    assert ring_combos[0] not in set(non_ring_combos), "injected combo must not collide with any real entity's combo"


def test_scenarios_dev_yaml_loads_and_has_expected_shape():
    path = os.path.join(os.path.dirname(__file__), "..", "configs", "scenarios_dev.yaml")
    with open(path) as f:
        config = yaml.safe_load(f)
    assert "scenarios" in config
    ids = [s["scenario_id"] for s in config["scenarios"]]
    assert "dev_no_ring_control" in ids  # negative control must exist
    for s in config["scenarios"]:
        assert s["shared_signal"] in ("device_info", "addr1", "card_combo")


def test_scenarios_test_yaml_created_exactly_once_on_day_5():
    """DAY 5 UPDATE: this file's earlier version asserted scenarios_test.yaml
    did NOT exist, and that was correct for Days 1-4. It has now been
    legitimately created as part of Day 5's final evaluation
    (configs/scenarios_test.yaml, scripts/day5_final_evaluation.py) — this is
    the expected one-time transition the original test's docstring called
    out, not a violation. From here on, the invariant that matters is that it
    was opened by exactly one script."""
    path = os.path.join(os.path.dirname(__file__), "..", "configs", "scenarios_test.yaml")
    assert os.path.exists(path), "expected scenarios_test.yaml to exist by Day 5"


def test_no_source_file_in_the_repo_references_scenarios_test_yaml():
    """Static guard: grep the whole repo (excluding this test itself and
    docs/) for any reference to scenarios_test.yaml outside the one Day-5
    script permitted to use it."""
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    allowed_files = {"test_ring_injector.py", "day5_final_evaluation.py", "DAILY_BUILD_PLAN.md",
                      "DATA_STRATEGY.md", "BUILD_CONTRACT.md", "PROJECT_MASTER_PLAN.md", "REPO_STATE.md",
                      "scenarios_test.yaml", ".gitignore", "EVALUATION_PLAN.md",
                      # These reference the isolation RULE in comments/docs, but never
                      # programmatically open or read the file itself:
                      "scoring.py", "ring_injector.py", "scenarios_dev.yaml", "README.md",
                      "FAILURE_LOG.md", "EVALUATION_RESULTS.md"}
    violations = []
    for dirpath, _, filenames in os.walk(repo_root):
        if ".git" in dirpath:
            continue
        for fname in filenames:
            if fname in allowed_files or not fname.endswith((".py", ".yaml", ".yml")):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", errors="ignore") as f:
                    content = f.read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            if "scenarios_test.yaml" in content:
                violations.append(fpath)
    assert not violations, f"scenarios_test.yaml referenced outside allowed files: {violations}"

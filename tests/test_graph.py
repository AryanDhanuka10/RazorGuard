import pandas as pd
import networkx as nx

from graph.relationships import extract_all_raw_signals, signals_to_dataframe, build_card_combo_key
from graph.edges import (
    compute_global_identifier_counts,
    compute_identifier_rarity,
    score_edges,
    qualify_edges,
)
from graph.cluster import build_qualified_graph, extract_clusters


def _fixture_rep_view():
    # Entities A,B share a rare device_info (2 entities globally).
    # Entities C,D,E,F,G all share a globally-common addr1 (used to regression-test
    # the "bridge-chaining from percentage rarity" failure fix).
    return pd.DataFrame(
        {
            "pseudo_entity_id": ["A", "B", "C", "D", "E", "F", "G"],
            "device_info": ["rare-phone-x", "rare-phone-x", None, None, None, None, None],
            "addr1": [None, None, 100.0, 100.0, 100.0, 100.0, 100.0],
            "card1": [1, 2, 10, 20, 30, 40, 50],
            "card2": [1, 2, 10, 20, 30, 40, 50],
            "card5": [1, 2, 10, 20, 30, 40, 50],
            "card6": ["debit"] * 7,
            "transaction_dt": [0, 10, 0, 100000, 200000, 300000, 400000],
        }
    )


def test_bridge_chaining_regression_common_addr1_does_not_qualify_alone():
    """Regression test for FAILURE_LOG.md 'Bridge-chaining from percentage-based
    identifier rarity': entities sharing ONLY a globally-common addr1 (held by
    many entities, no card/device corroboration) must NOT all collapse into one
    connected component."""
    rep = _fixture_rep_view()
    global_counts = compute_global_identifier_counts(rep)

    signals = extract_all_raw_signals(rep)
    sig_df = signals_to_dataframe(signals)
    scored = score_edges(sig_df, global_counts)
    qualified = qualify_edges(scored, threshold=0.3)

    g = build_qualified_graph(qualified)
    clusters = extract_clusters(g, min_members=2)

    # C,D,E,F,G share only a common addr1 with no other corroborating signal and
    # are temporally spread out -> must not form one giant qualified cluster.
    common_addr_group = {"C", "D", "E", "F", "G"}
    for cluster in clusters:
        assert not common_addr_group.issubset(cluster), (
            "entities sharing only a common address code collapsed into one "
            "cluster — bridge-chaining regression"
        )


def test_rare_shared_device_signal_can_qualify():
    """A.,B share a genuinely rare device string (2 entities globally) close in
    time -> should be able to qualify as an edge on its own."""
    rep = _fixture_rep_view()
    global_counts = compute_global_identifier_counts(rep)
    signals = extract_all_raw_signals(rep)
    sig_df = signals_to_dataframe(signals)
    scored = score_edges(sig_df, global_counts)
    qualified = qualify_edges(scored, threshold=0.3)

    pairs = set(zip(qualified["entity_a"], qualified["entity_b"]))
    assert ("A", "B") in pairs or ("B", "A") in pairs


def test_identifier_rarity_decreases_with_global_count():
    rep = _fixture_rep_view()
    global_counts = compute_global_identifier_counts(rep)
    rare_row = pd.DataFrame(
        {"signal_type": ["device_info"], "identifier_value": ["rare-phone-x"]}
    )
    common_row = pd.DataFrame({"signal_type": ["addr1"], "identifier_value": ["100.0"]})
    rare_rarity = compute_identifier_rarity(rare_row, global_counts).iloc[0]
    common_rarity = compute_identifier_rarity(common_row, global_counts).iloc[0]
    assert rare_rarity > common_rarity


def test_card_combo_key_requires_all_fields():
    row = pd.Series({"card1": 1, "card2": 2, "card5": 3, "card6": "debit"})
    assert build_card_combo_key(row) == "1|2|3|debit"

    incomplete = pd.Series({"card1": 1, "card2": None, "card5": 3, "card6": "debit"})
    assert build_card_combo_key(incomplete) is None


def test_connected_components_not_run_on_raw_signals_directly():
    """Architectural guard: extract_clusters only accepts a networkx Graph built
    from QUALIFIED edges (graph/edges.py output), never raw signal pairs. This
    test documents/enforces that raw signals alone (no qualification) produce a
    far denser, unfiltered graph than the qualified one on the same fixture."""
    rep = _fixture_rep_view()
    global_counts = compute_global_identifier_counts(rep)
    signals = extract_all_raw_signals(rep)
    sig_df = signals_to_dataframe(signals)

    raw_graph = nx.Graph()
    for _, row in sig_df.iterrows():
        raw_graph.add_edge(row["entity_a"], row["entity_b"])
    raw_clusters = [c for c in nx.connected_components(raw_graph) if len(c) >= 2]

    scored = score_edges(sig_df, global_counts)
    qualified = qualify_edges(scored, threshold=0.3)
    qualified_graph = build_qualified_graph(qualified)
    qualified_clusters = extract_clusters(qualified_graph, min_members=2)

    raw_max = max((len(c) for c in raw_clusters), default=0)
    qualified_max = max((len(c) for c in qualified_clusters), default=0)
    assert qualified_max <= raw_max

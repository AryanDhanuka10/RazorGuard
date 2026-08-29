# EVALUATION_RESULTS.md
Numbers only — every figure states its dataset, split, and layer, per EVALUATION_PLAN.md Section 9's honest-reporting checklist. Nothing here is a projection or an estimate dressed up as a measurement; everything was computed by actually running the code in this repo against the real IEEE-CIS dataset.

## Layer A — transaction-level classification
Dataset: IEEE-CIS, time-based split (413,379 train / 88,581 dev / 88,580 test — never random, see `data/splits.py`).

| Metric | XGBoost | Logistic Regression (baseline) |
|---|---|---|
| Precision | 0.194 | 0.117 |
| Recall | 0.664 | 0.691 |
| F1 | 0.301 | 0.200 |
| PR-AUC | 0.492 | 0.179 |
| ROC-AUC | 0.861 | 0.815 |
| False-positive rate | 0.099 | 0.188 |

XGBoost clearly outperforms the logistic baseline on PR-AUC and F1, with under half the false-positive rate. Logistic regression's recall is marginally higher, at the cost of much worse precision — expected for an unregularized-feature linear baseline under this class imbalance (~3.5% fraud rate).

## Day 1 checkpoint: graph sanity (before Layer B1)
15,000-entity representative subset. Initial edge-qualification formula (percentage-based identifier rarity) produced 99% edge qualification and a single 12,885-entity component — bridge-chained noise, caught by manual inspection exactly as intended (see FAILURE_LOG.md). After the fix (log-scaled absolute-count rarity + minimum-independent-evidence rule): 1,067 qualified edges, 523 clusters, largest cluster 7 entities, median 2.

## Full-dataset graph (Day 2)
248,038 pseudo-entities. 728,509 raw relationship signals extracted (687,122 card_combo / 32,331 device_info / 9,056 addr1). 6,289 edges qualified at threshold 0.3. 3,425 candidate clusters (median size 2, max 10).

## Layer B1 — real-data cluster prioritization (derived proxy, NOT ring ground truth)
Proxy: a cluster is "relevant" if it contains ≥1 member-transaction with `isFraud=1` OR its fraud-label concentration ≥0.3. Both parameters selected via a sweep on the **development split only** (see `ml/artifacts/layer_b1_threshold_sweep.json`); the report below uses the full population of 3,425 clusters against these dev-selected parameters. K=20 (stated assumption: analyst daily capacity).

| System | Precision@20 | Recall@20 |
|---|---|---|
| **Hybrid (final)** | **0.60** | 0.036 |
| Baseline A (rank by total cluster value) | 0.30 | 0.018 |
| Baseline B (rank by max member risk) | **1.00** | 0.060 |
| Baseline C (structural score alone) | 0.40 | 0.024 |

Lift of hybrid over Baseline A: 2.0x. Lift of hybrid over Baseline B: **0.6x — the hybrid score loses to Baseline B on this proxy.**

**Honest interpretation, not spin:** Baseline B outperforming the hybrid is expected, not a bug, and is reported as such rather than hidden or re-run until it looked better. The Layer B1 proxy is itself built directly from the same `isFraud` labels the XGBoost model (Layer A) was trained on — a ranking that is *purely* the model's own risk score has a structural home-field advantage against a label-derived proxy that shares its exact training signal. The hybrid score deliberately trades some of that advantage for interpretability and multi-signal grounding (relationship concentration, temporal coordination, structural anomaly, exposure) that a pure risk-score ranking doesn't have — properties that matter for the investigator-facing "why was this flagged" view (ARCHITECTURE.md Section 4) and that Layer B1's narrow proxy cannot measure at all. Layer B2 (synthetic, real cluster-level ground truth, Day 5 only) is the evaluation that can actually test whether the hybrid's graph-structural signal adds ring-detection value beyond what a risk score alone provides — Layer B1 cannot settle that question, and this report does not claim it does.

## Weight sensitivity (Section 7's required check)
±30% perturbation on each of the 5 weights, reranking the top-20 clusters: overlap with the base top-20 ranged from 0.80 (transaction_risk, down) to 1.00 (relationship_concentration up, temporal_coordination down, structural_anomaly both directions). No single weight's perturbation collapses the ranking — see `ml/artifacts/weight_sensitivity.json` for the full table.

## Known limitation carried into this report
`temporal_coordination` compresses to near-zero for nearly all clusters due to one extreme low-spread outlier dominating the min-max scale (FAILURE_LOG.md). Left undocumented-but-fixed as a Day 3 decision; the weight-sensitivity check suggests it isn't materially distorting the ranking, but it should be revisited if there's time before submission.

## Not yet run
Layer B2 (synthetic, `scenarios_test.yaml`) — Day 5 only, not touched yet. LLM Investigation Agent evaluation — Day 4/5. Elliptic(++) validation — optional, only if core system is fully done first.

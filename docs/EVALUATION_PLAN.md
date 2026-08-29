# EVALUATION_PLAN.md
**Status: FINAL / CANONICAL. Self-contained.**

## 1. Layer A — transaction-level classification
System: XGBoost vs. a simple baseline (logistic regression on raw features). Data: IEEE-CIS, time-based train/test split (not random — avoids leaking the same pseudo-entity's transactions across train and test). Metrics: Precision, Recall, F1, PR-AUC, ROC-AUC, false-positive rate.

## 2. Layer B1 — real-data cluster prioritization (derived proxy, explicitly labeled as such)
**The ground-truth problem:** IEEE-CIS provides only transaction-level fraud labels (`isFraud`), not cluster- or ring-level labels. Precision@K/Recall@K on real clusters is undefined unless cluster relevance is explicitly defined from what the data actually has.

**Defined proxy (documented, not hidden):** a candidate cluster is labeled "relevant" for this evaluation if it contains at least `N` transactions with `isFraud=1`, or its fraud-label concentration (fraction of members with `isFraud=1`) exceeds a stated threshold. `N` and the threshold are chosen on the development split (never on the final held-out split) and stated explicitly in the results write-up. **This proxy is never described as ring ground truth** — every reported number in this section is labeled "Layer B1 (derived proxy from transaction-level labels)."

**Systems compared** (all producing a ranked list of candidate clusters):
- Baseline A: rank by total cluster transaction value
- Baseline B: rank by maximum member transaction risk
- Baseline C: rank by graph-structural score alone (connected-components-derived concentration/temporal/structural-anomaly signal, no transaction risk)
- Final: normalized hybrid cluster score (PROJECT_MASTER_PLAN.md Section 7)

**Metrics:** Precision@K, Recall@K (K = analyst daily capacity, stated assumption e.g. K=20), lift over Baselines A and B specifically (not "beats random," which is too weak to be meaningful), fraud concentration surfaced.

**Threshold selection:** `MIN_CLUSTER_MEMBERS`, `MIN_INDEPENDENT_RELATIONSHIPS`, and the cluster-score threshold are all chosen using this Layer B1 proxy on the development split only (DATA_STRATEGY.md Section 6) — never using synthetic scenarios, since the injector isn't relevant to real-data threshold selection and shouldn't be conflated with it.

## 3. Layer B2 — synthetic ring evaluation (real cluster-level ground truth, by construction)
Data: `scenarios_test.yaml` only, opened exactly once at final evaluation (Day 5), after all detector logic and thresholds are frozen from Layer A/B1 work. No further tuning follows this run.
Metrics: cluster precision, cluster recall, entity-level precision/recall, cluster purity (fraction of a flagged cluster's members that are actually part of the injected ring vs. incidentally connected).
**Never mixed with Layer B1** — reported in its own section, explicitly labeled "synthetic scenario result."

## 4. Graph-based illicit-activity signal validation (Elliptic++, optional)
Data: Elliptic(++), native temporal train/test split. Metrics: Precision/Recall/F1 on labeled illicit/licit nodes using graph-derived features. Explicitly labeled: this validates that graph-derived signal correlates with real illicit activity on a dataset with genuine ground truth — it does **not** validate RazorGuard's connected-components extraction or its business performance, and is never merged with Layer A/B1/B2 numbers. Attempted only if the core system (Sections 1-3) is fully working.

## 5. LLM Investigation Agent evaluation
20-30 manually reviewed cases (mix of real flagged clusters and synthetic ring/no-ring cases, drawn from actual usage during Day 4-5, not only hand-picked examples).

| Metric | What it checks |
|---|---|
| Evidence faithfulness | Every claim in the agent's output traces to a cited evidence field |
| Unsupported-claim rate | Claims with no traceable evidence source |
| Schema validity | Structured output conforms to the defined contract (`escalate` / `insufficient_evidence`, confidence, cited bullets) |
| Insufficient-evidence correctness | Agent correctly outputs `insufficient_evidence` on weak cases rather than escalating |

## 6. False-positive analysis
False-positive rate at each policy tier; legitimate entities incorrectly escalated per 1,000 transactions; a precision-recall tradeoff curve shown explicitly (never collapsed to one accuracy number). Any investigation-cost figure used to weight this is a labeled scenario assumption with a stated sensitivity range, never presented as a real Razorpay operating cost.

## 7. Financial-claim discipline
Risk Score != Fraud Probability != Estimated At-Risk Exposure != Loss Prevented. `Estimated At-Risk Exposure = cluster fraud probability x cluster transaction value x recoverability assumption` (all three inputs shown). "Loss prevented" is never claimed anywhere — no intervention against real money was ever deployed. Only "surfaced" and "estimated exposure" language is used.

## 8. Data-split and leakage discipline (restated for this document)
Train split fits the ML model only. Development split selects all thresholds, weights, and the Layer B1 proxy parameters. `scenarios_dev.yaml` is used only for detector debugging, never for final threshold selection on real data. The final IEEE-CIS test split and `scenarios_test.yaml` are touched exactly once each, at the end, purely to report numbers — never to tune anything.

## 9. Honest reporting checklist (applied before submission)
- [ ] Every number states its dataset, split, and which layer (A / B1 / B2 / Elliptic-validation / LLM-eval) it belongs to
- [ ] Layer B1 numbers are explicitly labeled as a derived proxy, never as ring ground truth
- [ ] Layer B2 numbers are explicitly labeled as synthetic, never as real-world performance
- [ ] No "loss prevented" claim appears anywhere
- [ ] Elliptic(++) results, if present, are labeled "graph-signal validation," never "cluster/ring validation," and kept in their own section
- [ ] Baseline comparisons include Baselines A and B (value-sort, risk-sort), not just a random baseline
- [ ] LLM agent evaluation is reported as its own section with all four metrics from Section 5
- [ ] No threshold, weight, or normalization parameter was fit using `scenarios_test.yaml` or the final IEEE-CIS test split

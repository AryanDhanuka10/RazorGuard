# DATA_STRATEGY.md
**Status: FINAL / CANONICAL. Self-contained.**

## 1. Dataset comparison

| Requirement | IEEE-CIS Fraud Detection | Elliptic(++) Bitcoin | PaySim |
|---|---|---|---|
| Real-world data | Real e-commerce transactions | Real Bitcoin blockchain transactions | Fully simulated |
| Ground-truth labels | Real, transaction-level (`isFraud`) | Real, partial (2% illicit / 21% licit / 77% unknown) | Synthetic only |
| Meaningful entity relationships | Only derivable (heuristic fingerprints), not native | Native — edges are real fund flows | Simulated only |
| Suitable for graph/ring work | Weak — graph is inferred | Strong — already a real transaction graph | Weak |
| Hackathon-feasible scale | Yes (~590K rows) | Yes (203,769 nodes) | Yes, but fails the real-world requirement |
| Reproducible/public | Yes (Kaggle) | Yes (Kaggle/GitHub) | Yes, but synthetic |
| Supports meaningful evaluation | Yes at transaction level; no ring ground truth | Yes at node level; not payments-domain | Only against its own synthetic ground truth |

**Decision:** IEEE-CIS as primary (payments-domain relevant, real labels). Elliptic(++) as a narrow, secondary, explicitly-labeled graph-signal validation only. PaySim rejected as primary — it fails "real-world data" outright regardless of convenience.

## 2. IEEE-CIS — exact fields and honest semantics

| Field(s) | What's actually supported | What we will NOT call it |
|---|---|---|
| `card1`-`card6` | Card-related categorical/numeric attributes | NOT "credit card number" |
| `addr1`, `addr2` | Address-region categorical codes | NOT "home address" |
| `P_emaildomain`, `R_emaildomain` | Purchaser/recipient email domain | Kept as-is |
| `DeviceType`, `DeviceInfo` | Device category / logged device info string, inconsistently populated | "device fingerprint," NOT "device ID" |
| `id_01`-`id_38` | Undisclosed anonymized identity/behavioral features | "anonymized identity fingerprint" only |
| `TransactionAmt`, `TransactionDT`, `ProductCD` | As named | As named |

**Pseudo-entity key construction (produces graph NODES, not edges):** a derived key built from combinations of `card1+card2+addr1+D1`-style fields (a documented, widely-used Kaggle-community heuristic, not an official Vesta label) groups *transactions* likely from the same recurring payer into a single pseudo-entity. Disclosed everywhere as a **derived heuristic grouping**, not a verified identity link. This resolution step is complete before any relationship/edge logic runs — a pseudo-entity is a node in the graph, full stop, not itself evidence of a relationship to another node.

**Inter-entity relationship signals (produce graph EDGES, kept explicitly separate from the above):** once pseudo-entities exist as nodes, a *different* signal set determines whether an edge exists *between two distinct* pseudo-entities — e.g. entity A and entity B share a `DeviceInfo` value, or share an `addr1` code, or share a card-related combination, or transacted within a short time window. These are the raw relationship signals; whether they're strong enough to qualify as a real edge is a separate step (Section 4).

**Terminology discipline:** `DeviceInfo` is a logged, inconsistently-populated string (per the table above) — evidence language never says "the same device" or "linked accounts." UI/pitch/agent-output copy says "share an observed device-information signal" (or the equivalent for address/card signals). This applies everywhere the signal is surfaced, not just in this table.

## 3. Elliptic(++) — exact fields and honest semantics
203,769 nodes (each one Bitcoin transaction), 234,355 real directed edges (real fund flows), 49 timesteps, 166 base features (93 local + 72 one-hop aggregate — exact semantics of most features are undisclosed by the publisher beyond general local/aggregate categorization; described honestly as "undisclosed aggregate features," never invented interpretations). Labels: 4,545 illicit, 42,019 licit, 157,205 unknown. Used strictly for a graph-signal validation, reported in its own labeled section, never blended with IEEE-CIS-derived numbers, and only attempted if the core RazorGuard system is already fully working.

## 4. Preprocessing & canonicalization pipeline

```
Raw IEEE-CIS fields
    -> canonical feature table (typed, nulls handled, per-field semantics per Section 2)
    -> pseudo-entity key construction (documented heuristic, versioned) -> graph NODES
    -> raw inter-entity relationship signals between distinct pseudo-entities
       (shared device-information signal, shared address code, shared card-related
       combination, temporal proximity)
    -> edge evidence scoring (identifier rarity + independent-signal count + temporal
       proximity — PROJECT_MASTER_PLAN.md Section 4a)
    -> edge qualification (weak/globally-common edges filtered out; threshold tuned on
       the development split, never on test data)
    -> qualified graph edge list
```

Connected-components cluster extraction (DAILY_BUILD_PLAN.md Day 2) runs only on this qualified edge list — not on raw co-occurrence — which is what prevents a single common address code or an over-common device string from chaining unrelated pseudo-entities into one meaningless cluster.

All transformation logic lives in one auditable module (`data/canonicalize.py` for nodes, `data/relationships.py` for raw signals and qualification) so any graph edge traces back to the exact raw fields and the qualification decision that produced it.

## 5. Synthetic augmentation — scope and isolation
Narrow use: IEEE-CIS has no ring-level ground truth, so cluster/ring precision-recall cannot be measured on real data alone. A seeded ring injector generates labeled ring scenarios on top of real IEEE-CIS records (real transactions, synthetic *grouping* pattern) strictly to fill this one gap.

**Configuration isolation (hard rule):**
```
configs/
    scenarios_dev.yaml    <- used freely during Days 1-4: building, debugging, tuning
    scenarios_test.yaml   <- opened exactly once, at final evaluation (Day 5), never before
```
`scenarios_test.yaml` is never read, printed, or referenced in any detector-tuning code, notebook, or Day 1-4 activity — only in the one final evaluation script, run once, with no further tuning afterward. Dev and test scenario structures differ in ring topology, identifier-sharing pattern, and temporal spread so the test set isn't simply the training pattern re-labeled.

## 6. Threshold and configuration selection — data split discipline
```
Training split (IEEE-CIS)          -> fit XGBoost
Development split (IEEE-CIS)       -> select MIN_CLUSTER_MEMBERS, MIN_INDEPENDENT_RELATIONSHIPS,
                                       cluster-score threshold, and cluster-score weights,
                                       using the Layer B1 proxy (EVALUATION_PLAN.md Section 2)
scenarios_dev.yaml (synthetic)     -> used only for detector debugging/sanity checks, not for
                                       final threshold selection on real data
Freeze all configuration
scenarios_test.yaml (synthetic)    -> opened once, Day 5, for Layer B2 only — never influences
                                       any threshold chosen above
```
**Leakage rule (applies everywhere):** all preprocessing transformations, normalization parameters (e.g., min/max bounds for scaling), model fitting, and threshold selection are learned from training/development data only and applied unchanged to validation/test data. The test set (real held-out IEEE-CIS split, or `scenarios_test.yaml`) is never used to fit or select anything — only to report a final number, once.

## 7. Reproducibility
Fixed random seeds for the injector, the train/dev/test splits, and any stochastic step in modeling. Dataset versions pinned (Kaggle competition snapshot dates recorded in the README). `data/` scripts are the only path from raw download to processed tables — no manual spreadsheet edits.

# RazorGuard — PROJECT MASTER PLAN
**Track 2: AI Risk Manager — Razorpay AI Builder Internship 2026**
**Status: FINAL / CANONICAL. This document is self-contained — do not reference any prior version.**

## 0. Source of truth
Official facts (from razorpay.com/buildathon, fetched directly): 5 tracks including Track 2 (AI Risk Manager); deliverables are track selection, project name, what it solves, public GitHub repo, 5-minute pitch video, and "what broke and how you got out"; stipend ₹75,000/month, 6 or 12 months, Bangalore, applications close 5 Sept 2026. Organizer-verified evaluation criteria: **Problem Taste, Build Quality, AI Judgment, Failure Recovery**.

Track 2's official text states, verbatim: *"The bar: Honest metrics including false-positive cost. Strictly defense-only: anything offense-capable is disqualified."* This is a sourced official disqualification rule and is treated as non-negotiable throughout this project — the system flags, prioritizes, recommends, and escalates; it never autonomously blocks, reverses, or executes a financial action.

Anything not stated on the official page (exact scoring weights, team size, hosted-vs-recorded demo requirement) is **UNKNOWN — VERIFY WITH ORGANIZERS** and is never treated as fact in this plan.

## 1. Project name and pitch
**RazorGuard — Coordinated Risk Intelligence for Payment Investigations.**
Uses transaction-level risk scoring plus relationship analysis to surface coordinated suspicious activity, assemble evidence, and help a human investigator prioritize cases — never to act autonomously.

## 2. Problem Statement (~30 seconds)
A risk analyst at a payments company triages flagged accounts using a per-transaction fraud score that treats every account as independent. Coordinated abuse — many accounts sharing devices, payment instruments, or timing, deliberately kept under individual thresholds — is invisible to that score by construction. RazorGuard surfaces which *groups* of accounts look coordinated and risky, ranked by evidence-backed suspicion and estimated exposure, so investigation time goes where it matters most. Outcome: more at-risk exposure surfaced per unit of investigator time, with an honestly measured false-positive burden.

**Terminology discipline (applied everywhere in this project):** on real data, the system never claims to detect a "fraud ring" — IEEE-CIS has no ring-level ground truth to support that claim. It detects and ranks **coordinated suspicious clusters**. "Fraud ring" is used only for synthetic scenario testing, where ring structure is known by construction because we generated it.

## 3. Dataset
**Primary: IEEE-CIS Fraud Detection** (Kaggle) — real e-commerce transactions, real transaction-level fraud labels (`isFraud`), payments-domain relevant. Chosen over PaySim (fully simulated, fails the "real-world data" requirement outright) and over using Elliptic as primary (real graph, but Bitcoin-domain, not payments-relevant for Problem Taste).

**Secondary, narrow use: Elliptic(++) Bitcoin dataset** — 203,769 nodes (transactions), 234,355 real directed edges (real fund flows), partial ground truth (2% illicit, 21% licit, 77% unknown), 166 largely undisclosed aggregate features. Used **only** for a **graph-based illicit-activity signal validation**: checking whether graph-derived features correlate with real illicit/licit labels on a dataset with genuine ground truth. This does **not** validate RazorGuard's own connected-components extraction — it validates that graph signal in general carries information, on a different dataset, in a separate report section, never merged with IEEE-CIS results. Explicitly optional — attempted only if the core system is fully finished (see Section 11).

**Synthetic ring injector**: fills the one real gap — IEEE-CIS has no ring-level ground truth. Seeded, reproducible. Two clearly separated configs: `configs/scenarios_dev.yaml` (used freely during Days 1-4 for building/debugging/tuning) and `configs/scenarios_test.yaml` (opened exactly once, at final evaluation on Day 5, never before, never re-opened after, no further tuning follows).

**Pseudo-entity resolution (kept distinct from relationship signals — see Section 4):** pseudo-entity keys are derived from combinations of `card1/2`, `addr1`, and `D1`-style time-delta fields — a documented Kaggle-community heuristic for grouping *transactions likely from the same recurring payer*. This produces the graph's **nodes** (pseudo-entities), not its edges. `DeviceInfo` is intentionally reserved for later inter-entity relationship signals between distinct pseudo-entities. Documented everywhere as a **derived heuristic grouping**, never as a verified real-world identity link, and never described in UI or pitch copy as "the same device" or "the same person" — see Section 4's terminology rule.

## 4. Architecture

```
IEEE-CIS real transactions
    -> canonicalization (deterministic)
    -> transaction risk model (XGBoost)
    -> pseudo-entity resolution: transactions -> pseudo-entities (deterministic heuristic;
       pseudo-entities become graph NODES — this step is kept explicitly separate from
       relationship-signal extraction below, not conflated with it)
    -> inter-entity relationship signal extraction (raw shared signals BETWEEN distinct
       pseudo-entities: shared device-information signal, shared address code, shared
       card-related combination, temporal proximity)
    -> edge evidence scoring (identifier rarity + count of independent shared signals +
       temporal proximity — see Section 4a)
    -> edge qualification / weak-and-common-edge filtering (only qualified edges proceed —
       see Section 4a; this is the fix for connected-components' main failure mode)
    -> candidate cluster extraction via connected components, run ONLY on the qualified
       graph (deterministic — NOT community detection; no Louvain/Leiden/label-propagation
       is implemented)
    -> normalized hybrid cluster scoring (deterministic, weights sum to 1)
    -> deterministic evidence builder
    -> ONE Investigation Agent (LLM, evaluated — see Section 9)
    -> deterministic policy engine (4 tiers, human-approval gate, defense-only per the sourced Track 2 rule)
    -> human review
    -> append-only audit log (enforced — see Section 10)
```

### 4a. Edge qualification (new — fixes a real flaw in the original design)
Connected components, run over every weak or globally-common shared identifier, can chain unrelated entities together through incidental bridges (A-B strong, B-C weak, C-D near-noise all end up in one component). To prevent this, an edge only enters the graph if it passes an explicit, deterministic qualification stage:

```
edge_evidence_score = f(identifier_rarity, independent_signal_count, temporal_proximity)
```

- `identifier_rarity`: how uncommon the shared identifier value is across the whole dataset (a shared `addr1` held by thousands of accounts is weak evidence; one held by three accounts is strong).
- `independent_signal_count`: how many *distinct kinds* of identifier are shared between the same pair of pseudo-entities (device + card is stronger than device alone).
- `temporal_proximity`: how close in time the shared activity occurred.

An edge is **qualified** (kept in the graph that connected components runs on) only if `edge_evidence_score` clears a documented threshold, tuned on the development split alongside the other thresholds in Section 7 — using the same train/dev/test discipline (never fit on test data). Globally common identifiers are explicitly down-weighted so a common `addr1` region code alone cannot qualify an edge. This keeps connected components deterministic and hackathon-feasible while directly addressing the bridge-chaining failure mode — a Louvain/Leiden/GNN upgrade was considered and rejected as unnecessary once edge qualification is in place.

### 4b. Terminology discipline for evidence signals (new)
`DeviceInfo` and similar fields are, per DATA_STRATEGY.md Section 2, inconsistently populated logged strings, not verified device IDs. This must hold in every surface, not just the data-dictionary table: UI copy, the Investigation Agent's evidence bullets, the pitch script, and the README all say "share an observed device-information signal" (or "shared card-related signal," "shared address code," as appropriate) — never "share the same device," "are the same person," or "are linked accounts." The underlying evidence is real and worth surfacing; the *strength of claim* attached to it must match what the dataset actually supports.

## 5. AI Judgment — deterministic vs. ML vs. LLM

| Layer | Method | Why |
|---|---|---|
| transaction risk scoring | XGBoost | Tabular classification — a well-understood ML job, no reasoning needed |
| Relationship signal extraction + edge qualification | Deterministic (identifier rarity + independent-signal count + temporal proximity, Section 4a) | Filtering weak/common edges before clustering is exact, explainable logic — not a judgment call an LLM should make |
| Candidate cluster extraction | Deterministic — connected components, run on the qualified graph only | Purely structural once edges are qualified; no ambiguity an LLM would resolve better. A GNN and true community-detection algorithms (Louvain/Leiden) were considered and rejected — edge qualification addresses the main failure mode (bridge-chaining through weak edges) without that added complexity |
| Cluster scoring | Deterministic, documented formula (Section 7) | A weighted, normalized formula is fully explainable — required for the investigator-facing "why was this flagged" view |
| Evidence assembly | Deterministic | Retrieval, not reasoning |
| Case investigation & explanation | **One** LLM agent | The only place raw evidence needs weighing (does this evidence support escalation, or is it coincidence?) and needs to become a readable narrative |
| Action decision | Deterministic policy engine | Never delegated to the LLM — see Section 10 |

Exactly one agent. A second "explanation" agent over the same evidence would be reformatting, not new reasoning — deliberately not built.

## 6. Investigation Agent — contract
**Input:** deterministic evidence bundle only (cluster members, shared-identifier facts, temporal pattern, transaction risk scores, cluster score breakdown) — nothing else.
**Output (structured):** verdict (`escalate` / `insufficient_evidence`), confidence, evidence-grounded bullet explanation, a citation to a specific evidence field for every claim.
**Tools:** read-only queries over the already-assembled evidence bundle — no open-ended DB or web access, no state-changing tools.
**Hard rule:** if the evidence doesn't support a claim, output `insufficient_evidence` — never a filled-in guess.

## 7. Cluster Scoring (exact, normalized formula)
Runs on candidate clusters extracted from the **qualified** graph (Section 4a) — clusters formed by weak or globally-common edges never reach this stage.


```
cluster_score =
  w1 * normalized_relationship_concentration
+ w2 * normalized_transaction_risk
+ w3 * normalized_temporal_coordination
+ w4 * normalized_structural_anomaly
+ w5 * normalized_exposure

where w1 + w2 + w3 + w4 + w5 = 1
```

- `relationship_concentration`: fraction of a cluster's shared identifiers that are shared with 3+ other members — normalized to [0,1] directly (it's already a fraction).
- `mean_transaction_risk`: mean XGBoost score of cluster members — already in [0,1].
- `temporal_coordination`: inverse of activity time-spread within the cluster, min-max scaled to [0,1] within the evaluation window.
- `structural_anomaly`: cluster density relative to background graph density, min-max scaled to [0,1].
- `exposure`: `log1p(cluster_transaction_value)`, then min-max scaled to [0,1] — raw rupee values would otherwise dominate every other 0-1 component.
- **Minimum evidence requirement (configurable, not hardcoded):** `MIN_CLUSTER_MEMBERS` and `MIN_INDEPENDENT_RELATIONSHIPS` are parameters, swept and chosen from data (Section 9 of EVALUATION_PLAN.md), not fixed in advance.
- **Leakage rule:** all normalization parameters (min/max bounds, etc.) and all thresholds are fit on training/development data only and applied unchanged to validation/test data — never independently fit on test data.
- Weights (w1-w5) are documented as **initial assumptions** with a sensitivity check: rerank top-K clusters under ±30% weight perturbation, report how much the ranking changes.

## 8. Guardrails
Four tiers — low / medium / high / critical. Human approval required above low. **No auto-block or auto-reversal at any tier, ever** — this is the sourced official Track 2 rule (Section 0), not a discretionary choice. The system only ever flags, recommends, or escalates.

## 9. Evaluation — full methodology in EVALUATION_PLAN.md
Summary: **Layer A** (transaction-level, real IEEE-CIS labels, standard classification metrics). **Layer B1** (real-data cluster prioritization, using a documented derived proxy from transaction-level fraud labels — not real ring ground truth, always labeled as a proxy). **Layer B2** (synthetic ring evaluation, held-out `scenarios_test.yaml`, run exactly once on Day 5, real cluster-level ground truth). **LLM agent evaluation** (20-30 manually reviewed cases: evidence faithfulness, unsupported-claim rate, schema validity, insufficient-evidence correctness). **Optional Elliptic(++) graph-signal validation** (separate section, never merged with the above).

## 10. Audit logging — enforced, not just asserted
Append-only, not "immutable": no `UPDATE`/`DELETE` route exists on `/audit*` in the API router at all; the database role the app uses has `INSERT`/`SELECT` only on `audit_logs`, no `UPDATE`/`DELETE` grants. Hash-chaining was considered and explicitly not implemented for the hackathon build — a documented scope cut, not a silent omission. Logged per entry: timestamp, case ID, model/risk outputs, evidence used, agent output, policy decision, human action if applicable.

## 11. Final Scope (MVP)
In scope: IEEE-CIS ingestion, canonicalization/pseudo-entity resolution, XGBoost risk model, relationship-signal extraction + edge qualification, connected-components cluster extraction, normalized hybrid scoring, deterministic evidence builder, one Investigation Agent, deterministic policy engine, append-only audit log, Streamlit dashboard (built incrementally starting Day 2, not bolted on at the end — see Section 11a), full Layer A/B1/B2/LLM evaluation.

### 11a. Dashboard / evidence-view specification
The case-detail view is the single highest-leverage screen for the demo and must be built incrementally, not rushed on the last day. It shows, per flagged cluster:
```
TOP SUSPICIOUS CLUSTER
Coordinated Risk Score:   [0-100, from the normalized cluster score]
Estimated At-Risk Exposure: [Rupee figure, per Section 9/EVALUATION_PLAN.md — never called "loss prevented"]
Cluster Size:             [N pseudo-entities]

WHY FLAGGED (evidence bullets, each traceable to a real graph fact):
  - N entities share [an observed device-information signal / a rare address code / etc. — Section 4b language]
  - Activity concentrated within [time window]
  - Average member transaction risk: [score]
  - Estimated exposure: [figure]

[Relationship graph view — qualified edges only, visually distinguishable from
 rejected/filtered weak edges if shown at all]

Investigation Result: ESCALATE / INSUFFICIENT EVIDENCE
Reason: [Investigation Agent's cited explanation]
[Approve] [Reject] -> writes to audit log
```
A minimal version of this view (even ugly) starts Day 2-3 alongside the first real clusters, specifically so the project's core "does this actually help an investigator" value is validated early, not assembled for the first time during Day 5 integration.
Optional, attempted only if the above is fully working: Elliptic(++) graph-signal validation, weight sensitivity analysis beyond the basic check, hash-chained audit log.
Out of scope entirely: Kubernetes/Kafka/microservices, GNNs, deep learning, Isolation Forest or other redundant models, more than one LLM agent, any auto-block/auto-reversal capability.

## 12. Limitations (stated explicitly)
- IEEE-CIS's entity fingerprints are a derived heuristic, not verified real-world identity links.
- No real ring-level ground truth exists for IEEE-CIS; Layer B1's cluster relevance is a documented proxy from transaction-level labels, not confirmed ring membership.
- Synthetic ring ground truth (Layer B2) is only as realistic as the injector; results are reported as synthetic, never as real-world performance.
- Elliptic(++) validates a graph signal on a different domain (Bitcoin, not payments) — it does not measure this system's business performance.
- Cluster-score weights and minimum-evidence thresholds are tuned on held-out development data but remain assumptions, not production-calibrated values.
- Offline evaluation is not the same as production performance.
- The LLM agent's output is bounded by the evidence it's given — it can be wrong if the evidence itself is incomplete; its 20-30 case evaluation is a sanity check, not a statistically powered benchmark.
- Human review remains required for anything above low-risk; this is a decision-support tool, not an autonomous system.

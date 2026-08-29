# DAILY_BUILD_PLAN.md
**Status: FINAL / CANONICAL. Self-contained.** 5 build days. UNKNOWN whether an earlier internal deadline exists beyond the 5 Sept 2026 application close — verify with organizers and compress/extend if needed. Priority throughout: working end-to-end MVP early; UI starts Day 3, not Day 5; `scenarios_test.yaml` is touched exactly once, on Day 5, never before.

## DAY 1 — De-risk the graph first, THEN build infrastructure
**Objective:** Prove the core technical bet — that an IEEE-CIS-derived relationship graph produces sensible candidate clusters — on a representative subset, *before* investing in Docker/Postgres/audit permissions. If the graph is fundamentally garbage, that has to be discovered today, not after two days of infrastructure work.
**Tasks, strictly in this order:**
1. Data ingestion (pandas, in-memory is fine — no DB needed yet)
2. Canonicalization (`data/canonicalize.py`, field semantics per DATA_STRATEGY.md Section 2)
3. Pseudo-entity resolution (transactions -> pseudo-entities/nodes)
4. Small graph prototype on a representative subset: raw relationship-signal extraction + edge evidence scoring + edge qualification (PROJECT_MASTER_PLAN.md Section 4a)
5. Run connected components on the qualified subset graph and **manually inspect the resulting clusters** — do they look like plausible coordinated activity, or bridge-chained noise? This is the actual go/no-go checkpoint for the whole architecture.
6. **Only once Step 5 looks sane:** FastAPI `/health`, `/transactions/ingest` skeleton, Docker Compose + Postgres, `audit_logs` table with restricted grants (`INSERT`/`SELECT` only, no `UPDATE`/`DELETE` route in the router)
**Expected output:** A manually-reviewed set of candidate clusters from real data that look substantively reasonable, not obviously bridge-chained noise; infra (steps 6) stood up afterward.
**Tests/checkpoints:** pytest on canonicalization and pseudo-entity resolution. Manual review log of the Step 5 clusters (a few sentences: do these look real). Confirm no `UPDATE`/`DELETE` grant on `audit_logs`, once built.
**Git commits:** `feat: IEEE-CIS canonicalization`, `feat: pseudo-entity resolution`, `feat: relationship-signal extraction + edge qualification (prototype)`, `chore: manual cluster sanity review`, `init: docker-compose + FastAPI skeleton`, `feat: append-only audit schema`.
**Stop adding features when:** Step 5's clusters look sane and infra is stood up. **If Step 5 looks wrong, stop and fix edge qualification thresholds before touching infrastructure at all** — that's the whole point of this day's ordering.

## DAY 2 — Scale the graph to full data + transaction ML + first ugly UI
**Objective:** XGBoost baseline trained and Layer A evaluated; Day 1's graph prototype (relationship signals + edge qualification + connected components) scaled from the representative subset to the full dataset; Baseline C implemented; a bare, unstyled cluster-list UI started (per the "start UI early, even ugly" correction).
**Tasks:** Train XGBoost on the training split, evaluate Layer A on the held-out test split (Precision/Recall/F1/PR-AUC/ROC-AUC/FP-rate). Run the Day-1 relationship-signal extraction + edge qualification + connected-components pipeline over the full dataset. Implement Baseline C (structural score, unnormalized is fine at this stage). Start a bare-bones Streamlit page: just a list of candidate clusters and their raw evidence signals, no styling — this is intentionally ugly, it exists to keep the "does this look useful" question alive every day, not just at the end.
**Expected output:** `/graph/build` produces real candidate clusters from the full dataset, using the qualified-edge approach validated on Day 1; Layer A metrics logged; an ugly cluster list renders in Streamlit.
**Tests/checkpoints:** pytest on graph construction + edge qualification + cluster extraction against a small fixture with known expected clusters. Layer A numbers recorded, whatever they actually are. Spot-check that full-dataset clusters still look sane, same manual-review habit as Day 1.
**Git commits:** `feat: XGBoost baseline + Layer A eval`, `feat: full-dataset relationship graph + edge qualification`, `feat: candidate cluster extraction (connected components, qualified graph)`, `feat: baseline-C structural score`, `feat: bare cluster-list UI (unstyled)`.
**Stop adding features when:** candidate clusters are extractable from the full dataset, Layer A is measured, and the ugly UI renders real clusters — normalized hybrid scoring and the styled case-detail view are Day 3's job.

## DAY 3 — Normalized hybrid scoring + Layer B1 evaluation + real case-detail UI
**Objective:** Normalized hybrid cluster score implemented; `MIN_CLUSTER_MEMBERS`/`MIN_INDEPENDENT_RELATIONSHIPS`/cluster-score threshold/edge-qualification threshold chosen using the Layer B1 proxy on the development split (real data only — no synthetic data exists yet); Layer B1 evaluation run (Baselines A/B/C vs. hybrid); the styled case-detail view (PROJECT_MASTER_PLAN.md Section 11a) built out from Day 2's ugly list.
**Tasks:** Implement normalization (log1p + min-max for exposure; min-max for temporal/structural components; concentration and risk are already [0,1]) — all parameters fit on train/dev, never on test. Define and document the Layer B1 proxy (EVALUATION_PLAN.md Section 2). Sweep the minimum-evidence and edge-qualification thresholds on the development split and pick values from the results. Run Layer B1 (Precision@K/Recall@K/lift vs. Baselines A and B). Upgrade Day 2's bare cluster list into the real case-detail view: score, estimated exposure, cluster size, evidence bullets (using Section 4b terminology), a basic relationship-graph rendering.
**Expected output:** `/clusters` returns normalized-score-ranked clusters; Layer B1 numbers logged and labeled as a derived-proxy result; the dashboard now looks like the Section 11a spec, even if rough.
**Tests/checkpoints:** pytest confirming weights sum to 1 and every component is in [0,1]. Layer B1 comparison table produced, whether or not the hybrid clearly wins.
**Git commits:** `feat: normalized hybrid cluster scoring`, `feat: layer-b1 proxy + threshold selection`, `feat: layer-b1 evaluation`, `feat: case-detail evidence view`.
**Stop adding features when:** Layer B1 is measured and logged honestly, and the case-detail view shows real clusters with evidence — no synthetic data work starts today.

## DAY 4 — Policy engine + Investigation Agent + synthetic dev-only work
**Objective:** Deterministic policy engine with its guardrail test; the single Investigation Agent wired to real evidence; seeded ring injector built and used **only via `scenarios_dev.yaml`** — `scenarios_test.yaml` is not touched today.
**Morning:** Policy engine (4 tiers, human-approval gate). Guardrail pytest (release gate, never weakened): for any input, the policy engine never returns an auto-block/auto-reversal action. Build the ring injector; use only `scenarios_dev.yaml` for building/debugging/sanity-checking the detector.
**Afternoon:** Investigation Agent per ARCHITECTURE.md Section 4 — structured output, per-claim citations, `insufficient_evidence` as a valid output, no state-changing tools.
**Evening:** Evidence-grounding review pass on real cases and `scenarios_dev.yaml`-based synthetic cases — manually check for unsupported claims, fix any found, and log these toward the 20-30 case LLM evaluation set (do not open `scenarios_test.yaml` for this).
**Expected output:** `/clusters/{id}/investigate` produces cited cases or explicit `insufficient_evidence` verdicts; policy tiers assign correctly; the detector has been sanity-checked against dev-only synthetic scenarios.
**Tests/checkpoints:** Guardrail test passes, unmodified. Evidence-grounding spot check on at least 5 real cases and 2 dev-scenario synthetic cases.
**Git commits:** `feat: deterministic policy engine`, `test: guardrail - no auto-block ever`, `feat: seeded ring injector (dev config only used)`, `feat: investigation agent`, `chore: evidence-grounding review pass`.
**Stop adding features when:** at least one real flagged case and one `insufficient_evidence` case both work end to end (these become the demo's Scenario A and B) — and confirm `scenarios_test.yaml` has not been opened.

## DAY 5 — Freeze, final synthetic evaluation, integration, docs, deployment, pitch
**Objective:** Freeze all detection logic and thresholds from Days 1-4. Open `scenarios_test.yaml` exactly once for Layer B2. Complete the LLM evaluation set. Finish the dashboard, docs, failure log, and pitch.
**Tasks, in order:**
1. **Freeze** — no further changes to thresholds, weights, or detector logic after this point.
2. Open `scenarios_test.yaml` for the first and only time; run Layer B2 (cluster precision/recall, entity precision/recall, cluster purity); record results once, no re-tuning afterward.
3. Complete the LLM evaluation set to 20-30 cases and report the four metrics (EVALUATION_PLAN.md Section 5).
4. Finish the Streamlit dashboard: both demo scenarios, evidence view, estimated-exposure display, approve/reject wired to audit-log writes.
5. Finish README, and confirm ARCHITECTURE.md/DATA_STRATEGY.md/EVALUATION_PLAN.md/PROJECT_MASTER_PLAN.md all match what's actually built.
6. Fill FAILURE_LOG.md honestly from the week's actual issues, with evidence links/commits per entry.
7. Record the 5-minute pitch (two scenarios, one real failure and recovery, honest metrics, explicit limitations).
**Optional, only if all of the above is fully finished:** Elliptic(++) graph-signal validation notebook, run and reported in its own labeled section.
**Expected output:** Deployed or reliably local-demoable system; pitch video; public repo; every doc claim matches the repo.
**Tests/checkpoints:** Full run-through timed against 5 minutes, at least twice. Confirm `scenarios_test.yaml` was opened exactly once.
**Git commits:** `chore: freeze detection config`, `feat: layer-b2 final evaluation`, `feat: llm evaluation results`, `feat: full dashboard integration + audit writes`, `docs: failure log + limitations`, `chore: deployment config`, `release: submission v1`.
**Stop adding features when:** the two-scenario demo runs cleanly and every doc claim matches the repo. Elliptic validation is the first thing cut if time runs short.

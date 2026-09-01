# FAILURE_LOG.md

**Status: FINAL / CANONICAL TEMPLATE**

This file records genuine engineering failures encountered during the RazorGuard build.

Do not pre-write failures.

Do not invent failures to make the project appear more complex.

Do not remove a meaningful failure merely because it was eventually fixed.

The buildathon evaluates **Failure Recovery**, so honest engineering evidence is more valuable than a clean-looking history.

---

# How to Use This Log

Create an entry when something materially breaks, fails, produces an unexpected result, exposes a flawed assumption, or forces a design change.

Examples include:

* dataset assumptions proving incorrect,
* missing or unexpectedly sparse fields,
* time-based split leakage risks,
* pseudo-entity resolution producing poor groupings,
* graph bridge-chaining,
* runaway connected-component sizes,
* weak edge qualification,
* unexpected model performance,
* normalization bugs,
* memory or performance problems,
* policy-engine edge cases,
* Investigation Agent hallucinations or unsupported claims,
* malformed structured output,
* synthetic scenario isolation mistakes,
* database permission failures,
* deployment or integration failures.

Do not force an entry for every bug.

Minor syntax errors or trivial typos generally do not belong here unless they reveal a meaningful process failure.

---

# Failure Entry Template

Copy the following section for each genuine incident.

---

## [Short Title of What Broke]

**Day/date:**

**Area:**
Dataset / Canonicalization / Pseudo-Entity Resolution / Graph / Edge Qualification / ML / Cluster Scoring / Evaluation / Policy / Investigation Agent / UI / Database / Infrastructure / Synthetic Evaluation / Other

### Problem

What happened concretely?

Include:

* the error,
* unexpected output,
* bad result,
* blocker,
* failed assumption,
* or violated expectation.

Do not write vague statements such as:

> "The graph was not working."

Instead describe the observable failure.

---

### Why It Happened

Once understood, describe the root cause.

Distinguish the root cause from the visible symptom.

If the root cause remains uncertain, state that honestly.

---

### What Was Tried

List attempted fixes or investigations.

Include approaches that did not work.

Do not rewrite history to make the final solution look obvious.

---

### What Failed and Why

Document meaningful dead ends.

Examples:

* a threshold adjustment that did not fix bridge chaining,
* a model feature that caused leakage,
* a refactor that introduced regressions,
* an approach that was too slow at full dataset scale.

These failed approaches may be useful evidence of engineering judgment.

---

### What Finally Worked

Describe the actual fix or recovery.

Be precise about what changed.

---

### What Changed in the System

Record the resulting change to:

* code,
* architecture,
* configuration,
* thresholding,
* evaluation methodology,
* testing,
* process,
* or documentation.

If nothing structural changed, state that explicitly.

---

### Guardrail / Evaluation Check

Record whether the recovery preserved:

* defense-only constraints,
* no-auto-block/no-auto-reversal behavior,
* evaluation isolation,
* train/development/test separation,
* `scenarios_test.yaml` isolation.

If any of these were involved in the failure, document exactly what happened.

---

### Evidence

Include relevant evidence where available:

* error output,
* test output,
* screenshot,
* experiment result,
* benchmark,
* cluster inspection,
* commit,
* issue,
* pull request.

Do not claim evidence exists if it was not recorded.

---

**Commit:**

**Issue/PR:**

---

# Candidate Categories to Watch For

These are examples, not a checklist to force-fill.

## Dataset Issues

* missing fields,
* unexpected null patterns,
* incorrect assumptions about field meaning,
* time-based split problems,
* leakage risk.

## Graph Construction Issues

* wrong edge semantics,
* pseudo-entity grouping problems,
* raw signals accidentally treated as qualified edges,
* bridge chaining,
* runaway cluster sizes,
* sparse or uninformative pseudo-entity fingerprints.

## Edge Qualification Issues

* globally common identifiers dominating connectivity,
* insufficient independent evidence,
* temporal proximity producing unintended links,
* threshold choices creating either an empty graph or giant components.

## Model Issues

* class imbalance surprises,
* logistic regression outperforming XGBoost,
* unstable metrics,
* unexpected false-positive burden,
* features leaking temporal information.

## Cluster Scoring Issues

* one component dominating despite normalization,
* unstable rankings,
* normalization parameters incorrectly fit,
* exposure dominating prioritization,
* sensitivity to weight assumptions.

## Evaluation Issues

* Layer A/B1/B2 results accidentally mixed,
* Layer B1 proxy ambiguity,
* test data influencing thresholds,
* synthetic development and synthetic test scenarios being conflated.

## Investigation Agent Issues

* unsupported claims,
* evidence citations not matching claims,
* malformed structured output,
* over-escalation,
* failure to use `insufficient_evidence`,
* claims stronger than the deterministic evidence supports.

## Policy Issues

* an input path producing an automatic block or reversal,
* policy behavior depending on LLM output beyond its allowed role,
* guardrail test exposing an edge case.

## Infrastructure Issues

* database permission errors,
* audit-log constraints failing,
* Docker environment problems,
* API integration failures,
* full-dataset memory or performance problems.

## Synthetic Isolation Issues

* accidental reference to `scenarios_test.yaml` before Day 5,
* synthetic test data influencing threshold selection,
* detector logic changing after final Layer B2 evaluation.

Any synthetic-test isolation failure is serious and must be documented honestly.

---

# Writing Rules

Each entry must distinguish:

```text
Symptom
    ↓
Root cause
    ↓
Attempts
    ↓
Failed approaches
    ↓
Actual recovery
    ↓
Resulting system change
```

Do not write:

> "There was an issue, but we fixed it."

That contains no useful engineering information.

---

# For the Final Pitch

At the end of the build, select one or two genuine failures that best demonstrate:

* sound diagnosis,
* willingness to challenge an incorrect assumption,
* technically justified recovery,
* a meaningful design improvement.

Prefer failures where the recovery changed the design rather than merely fixing a typo.

Do not exaggerate the failure.

Do not claim a failure was more serious than the evidence shows.

The strongest Failure Recovery story is one where:

1. a reasonable assumption turned out to be wrong;
2. the failure was detected through testing, evaluation, or inspection;
3. an initial fix did not fully solve the problem;
4. the root cause was identified;
5. the final solution improved the architecture;
6. the resulting evidence can be shown.

---

# Current Failure Entries

---

## Device info silently null after merge

**Day/date:** Day 1, 2026-08-29

**Area:** Canonicalization

### Problem
After running `canonicalize_transactions` + `canonicalize_identity` + `merge_transaction_identity` on the full real IEEE-CIS dataset, `device_info` and `device_type` were **100% null** — even though the raw `train_identity.csv` clearly has real values (e.g. `"SAMSUNG SM-G892A Build/NRD90M"`, `"iOS Device"`) for ~20-24% of transactions.

### Why It Happened
`canonicalize_transactions()` listed `DeviceType`/`DeviceInfo` in its required-columns map even though those fields only exist in the identity table. Since the raw transaction table never has these columns, the function created them as **all-NaN placeholders** under the canonical names `device_type`/`device_info`. Separately, `canonicalize_identity()` was only renaming `TransactionID`, so it kept the identity table's device columns under their **raw** names (`DeviceType`/`DeviceInfo`). The merge then produced two device-related columns per field — the real data sitting under the raw name, and an all-NaN column sitting under the canonical name that all downstream code was actually going to read from.

### What Was Tried
Ran canonicalization first on a 20,000-row sample — device_info showed 100% null there too, which looked at first like a legitimate data-sparsity finding consistent with "inconsistently populated" (DATA_STRATEGY.md Section 2), not obviously a bug.

### What Failed and Why
Initially almost accepted the 100%-null result as "device_info is just this sparse in the sample," since DATA_STRATEGY.md already primes the expectation that this field is inconsistently populated. Rerunning on the full 590,540-row dataset (not just the sample) still showed 100% null, which is what triggered actually inspecting the merged column names rather than trusting the aggregate stat.

### What Finally Worked
Inspected the merged DataFrame's actual columns and found both `device_info` (all-NaN) and `DeviceInfo` (real data) present simultaneously. Removed `DeviceType`/`DeviceInfo` from `canonicalize_transactions()`'s field map entirely (they never legitimately come from the transaction table) and added an explicit `IDENTITY_CANONICAL_FIELDS` rename map to `canonicalize_identity()` so the real values land under the canonical lowercase names.

### What Changed in the System
`data/canonicalize.py`: removed `DeviceType`/`DeviceInfo` from `CANONICAL_FIELDS` (transaction side); added `IDENTITY_CANONICAL_FIELDS` and applied it in `canonicalize_identity()`. Re-verified on the full dataset: `device_info` null rate is now 79.9%, `device_type` 76.2% — consistent with "inconsistently populated," now for a real reason instead of a merge bug.

### Guardrail / Evaluation Check
No detector logic, thresholds, or synthetic scenarios were involved — this was caught before any relationship-signal or graph work began, so no downstream tuning was contaminated by the bad column.

### Evidence
Before fix: `device_info` null rate 1.0 on both a 20k-row sample and the full 590,540-row dataset.
After fix: `device_info` null rate 0.7990551, `device_type` null rate 0.7615572, verified by direct execution against `data/raw/train_transaction.csv` + `data/raw/train_identity.csv`.

**Commit:** `fix: canonicalization was silently nulling device_info/device_type after merge`

**Issue/PR:** (none — single-session fix during Day 1 verification)

---

## Pseudo-entity resolution OOM-killed at full dataset scale

**Day/date:** Day 1, 2026-08-29

**Area:** Pseudo-Entity Resolution / Infrastructure (memory)

### Problem
`resolve_pseudo_entities()` ran fine on small fixtures but was killed (`returncode 137` / OOM) twice when run against the full 590,540-row dataset: once using a row-wise `df.apply(fingerprint_fn, axis=1)` implementation, and again — after vectorizing the hashing itself — when the input frame still carried all 434 canonical columns (including 339 `V*` risk features not needed for this step).

### Why It Happened
Two compounding causes: (1) `df.apply(..., axis=1)` materializes a Python `Series` object per row, which does not scale to ~590K rows on a ~3.9GB-RAM sandbox; (2) even after that was fixed with a vectorized `pd.factorize` approach, the function was still receiving the full wide canonical table (`df.copy()` on a ~1.2GB frame with 434 columns) when pseudo-entity resolution only needs 4 key fields plus a few aggregation fields — most of the memory pressure was columns this step never touches.

### What Was Tried
1. Vectorized the key-hashing (composite string key + `pd.factorize`, hash only unique keys) — fixed the row-wise slowness but the process was still killed on the full dataset.
2. Checked `free -h` and the actual per-column memory footprint via `pyarrow.parquet.read_schema` to find the real bottleneck rather than guessing.

### What Failed and Why
Assuming the vectorized fingerprinting fix alone would be enough — it fixed the *algorithmic* inefficiency but not the *memory footprint* of operating on the full 434-column frame, which was the actual proximate cause of the second kill.

### What Finally Worked
Loaded only the 8 columns pseudo-entity resolution and its aggregation actually need (`pd.read_parquet(path, columns=[...])`, using parquet's columnar read to avoid pulling the ~339 `V*` columns into memory at all). This slim frame is ~16MB instead of ~1.2GB; resolution then completed in 2.3 seconds.

### What Changed in the System
`data/pseudo_entity.py`: replaced row-wise `.apply()` with vectorized `pd.factorize` over a composite string key. No change to the pseudo-entity heuristic itself (`card1+card2+addr1+d1`, unchanged) — this was purely a performance/memory fix, not a change to grouping logic. The verification workflow now explicitly loads a column-limited slim frame for this step rather than passing the full canonical table through every stage.

### Guardrail / Evaluation Check
No thresholds or synthetic scenarios involved. Pseudo-entity heuristic version string (`v1-card1_card2_addr1_d1`) unchanged, so no silent redefinition of the grouping logic occurred alongside the performance fix.

### Evidence
Full-dataset run after both fixes: 590,540 transactions -> 248,038 unique pseudo-entities; 65,878 entities with more than one transaction (recurring payers), 182,160 singleton entities. Resolve time 2.3s on the slim frame.

**Commit:** `fix: vectorize pseudo-entity resolution + load slim column subset to fix OOM at full scale`

**Issue/PR:** (none — single-session fix during Day 1 verification)

---

## Bridge-chaining from percentage-based identifier rarity (Day 1 go/no-go checkpoint failure)

**Day/date:** Day 1, 2026-08-29

**Area:** Graph / Edge Qualification

### Problem
Running the Day 1 Step 5 prototype (relationship-signal extraction + edge qualification + connected components on a representative 15,000-entity subset of real data) produced exactly the failure mode edge qualification is supposed to prevent: 1,408,297 of 1,423,360 raw signals (99%) qualified as edges, and connected components collapsed **12,885 of the 15,000 sampled entities into a single component**. This is bridge-chained noise, not coordinated clusters, and is the actual go/no-go signal DAILY_BUILD_PLAN.md Day 1 exists to catch before any infrastructure work.

### Why It Happened
`identifier_rarity` was computed as `1 - (fraction of the TOTAL ENTITY POPULATION sharing this identifier value)`, with a "globally common" cap at 15% population share. This looked reasonable in the abstract but breaks down for low-cardinality identifier fields: `addr1` has only 332 distinct values across 248,038 entities (~747 entities per value on average). No population-*percentage* cutoff can distinguish "common" from "rare" for a field with that little cardinality — a value held by 16,465 entities is only ~6.6% of the population, comfortably under the 15% cap, yet is obviously not meaningful evidence of coordination. The percentage framing was the wrong lens entirely, not just a badly-tuned cap.

### What Was Tried
1. First hypothesis: rarity was being computed from the local 15,000-entity *subset* instead of the global population, so a globally-common value could look artificially rare in a small sample. Checked this directly by comparing subset-based vs. global prevalence for the top addr1 values — they were nearly identical (subset was a good random sample), so this was **not** the actual cause, just a plausible-sounding one that had to be ruled out with real numbers before moving on.
2. Checked actual cardinality of `addr1` (332 values) and `device_info` (1,119 values) against the entity population — this revealed the real problem: percentage-of-population is structurally the wrong measure for low-cardinality fields.

### What Failed and Why
The subset-vs-global-population hypothesis (Attempt 1) failed to explain the observed 99% qualification rate — the numbers matched almost exactly, so "wrong denominator source" was not the bug, even though it looked like an obvious candidate. Chasing it further would have produced a fix that didn't address the actual failure.

### What Finally Worked
Replaced the percentage-based rarity with an absolute-count, log-scaled formula: `rarity = 1 / (1 + log1p(global_entity_count_sharing_this_value))`, computed once from the full 248,038-entity representative view via `compute_global_identifier_counts()`. This naturally gives a value shared by 2 entities a rarity of ~0.48 and a value shared by 16,000+ entities a rarity of ~0.09, without needing an arbitrary percentage cutoff. Additionally added a minimum-independent-evidence qualification rule (documented as an implementation decision, not canon, per BUILD_CONTRACT.md Section 15): a pair qualifies only if 2+ distinct signal types corroborate it, OR a single signal type is present but its own rarity clears a high bar (0.4) — because even after the rarity fix, a lone weak `addr1` match combined only with temporal proximity was still occasionally clearing the base threshold.

### What Changed in the System
`graph/edges.py`: replaced `compute_identifier_rarity`'s percentage-of-population formula with the log-scaled absolute-count version; added `compute_global_identifier_counts()`; added the minimum-independent-evidence rule to `qualify_edges()`; lowered `EDGE_QUALIFICATION_THRESHOLD` from an initial 0.45 guess to 0.3 (still a Day-1 prototype default — final value gets swept on Day 3 against the Layer B1 proxy, per EVALUATION_PLAN.md Section 2, not decided here).

### Guardrail / Evaluation Check
This is exactly what edge qualification and the Day 1 checkpoint exist to catch, and it was caught before any infrastructure, ML, or policy work began — no downstream component was contaminated by the broken rarity formula. `scenarios_test.yaml`/`scenarios_dev.yaml` were not involved (still real-data only at this stage, correctly, per DATA_STRATEGY.md Section 6).

### Evidence
Before fix: 15,000-entity subset -> 1,408,297/1,423,360 signals qualified, largest component 12,885 entities.
After fix (threshold=0.3, with the min-independent-evidence rule): 1,067 qualified edges, 523 clusters, largest cluster 7 entities, median cluster size 2. Manual inspection of the largest resulting cluster showed 5 of 7 entities sharing an identical `card1+card2+card5+card6+addr1` combination — a plausible same-instrument-different-pseudo-entity pattern, not obvious noise.

**Commit:** `fix: replace percentage-based identifier rarity with log-scaled absolute-count rarity; add minimum-independent-evidence qualification rule`

**Issue/PR:** (none — single-session fix during Day 1 verification)

---

## Recurring pattern: full wide-table loads OOM-kill at ~590K rows x 400+ columns

**Day/date:** Day 1-2, 2026-08-29

**Area:** Infrastructure (memory) / Dataset

### Problem
Three separate steps (pseudo-entity resolution, entity representative-view build, and Layer A model training) were each killed (`returncode 137`) the first time they were run against the full `canonical_full.parquet` table (590,540 rows x 434-436 columns, ~1.2GB as a pandas DataFrame) in this sandbox's ~3.9GB RAM.

### Why It Happened
Each step only needs a small subset of the 434 canonical columns (pseudo-entity resolution needs 4 key fields; risk modeling needs the `V`/`C`/`D` feature columns, not device/address/card identity fields), but the working scripts were loading the *entire* canonical table via `pd.read_parquet(path)` with no column filter, then keeping multiple copies alive (`.copy()`, intermediate DataFrames, `float64` numpy arrays) simultaneously.

### What Was Tried / What Finally Worked
Each time: switched to `pd.read_parquet(path, columns=[...])` to load only the columns that step actually needs (parquet's columnar format makes this cheap), downcast numeric columns to `float32`/smaller int types, and explicitly `del` + `gc.collect()` intermediate frames before the next heavy allocation.

### What Changed in the System
No change to any detection/modeling logic — purely a memory-handling pattern now applied consistently: every script that reads `canonical_full.parquet` for a specific stage loads a column-limited slice rather than the full table. This is documented here once as a recurring pattern rather than three near-duplicate log entries, per this file's own instruction not to force an entry for every incident once the pattern is understood.

### Guardrail / Evaluation Check
No effect on train/dev/test split integrity, thresholds, or synthetic isolation — purely a compute/memory fix, verified by each step completing successfully and producing the same logical results after the fix (e.g. pseudo-entity counts, Layer A metrics) as intended.

### Evidence
Pseudo-entity resolution: killed on full 434-column load, succeeded in 2.3s on an 8-column slim load. Layer A training: killed on full-column load, succeeded (XGBoost trained in 50.7s) after switching to a 370-column feature-only load with float32 downcasting.

**Commit:** (rolled into the same commits as the pseudo-entity and Layer A work)

**Issue/PR:** (none — single-session fixes during Day 1-2 verification)

---

## Combinatorial signal explosion from large shared-identifier groups at full scale

**Day/date:** Day 2, 2026-08-29

**Area:** Graph / Edge Qualification (scaling the Day 1 prototype to the full dataset)

### Problem
Running `extract_all_raw_signals` on the full 248,038-entity representative view (the Day 2 task of scaling Day 1's validated approach to full data) was killed (OOM). The Day 1 prototype used a 15,000-entity subset and a `max_group_size=500` cap without issue, so this wasn't anticipated.

### Why It Happened
Exact pair counting (not just re-running and hoping) showed `card_combo` groups near the 500-member cap each produce up to C(500,2)=124,750 pairs via `itertools.combinations`, and summed across the full dataset this produced **~11.5 million** `RawSignal` dataclass instances before qualification even ran — far more Python-object memory than the 15,000-entity Day 1 subset ever produced (its largest groups were much smaller by chance).

### What Was Tried
Computed the exact expected pair count under caps of 500/200/100/50/30 before touching the pipeline again, rather than guessing-and-rerunning: cap=500 -> ~11.5M pairs, cap=100 -> ~1.58M, cap=50 -> ~729K (comparable in order of magnitude to the ~1.4M signals the Day 1 subset produced successfully).

### What Failed and Why
N/A — this was caught by computing the pair count directly rather than by a failed retry; no wasted implementation attempt.

### What Finally Worked
Lowered `max_group_size` from 500 to 50. The excluded large groups are exactly the ones edge qualification's rarity scoring already down-weights to near-zero (a card-combination shared by 200+ pseudo-entities is not meaningfully "rare" under the log-scaled rarity formula regardless), so this trades a small amount of already-low-value signal for the memory headroom needed to run at full scale.

### What Changed in the System
`graph/relationships.py`: `max_group_size` default changed from 500 to 50, with the reasoning documented in the function's docstring so a future re-tuning doesn't have to rediscover this.

### Guardrail / Evaluation Check
No change to the qualification formula or thresholds themselves — this only changes which raw signals are ever generated in the first place, and only for groups already expected to score near-zero. Train/dev/test split and synthetic scenario isolation unaffected (still real-data only).

### Evidence
Exact pair-count check: cap=500 -> 11,498,825 pairs; cap=50 -> 728,509 pairs. Full-dataset run after the fix completed and produced clusters (see Day 2 completion note in this log / REPO_STATE.md for the resulting cluster statistics).

**Commit:** `fix: lower max_group_size 500->50 to fix full-dataset OOM in relationship-signal extraction`

**Issue/PR:** (none — single-session fix during Day 2 verification)

---

## Stale duplicate default silently undid the group-size cap fix

**Day/date:** Day 2, 2026-08-29

**Area:** Graph / Edge Qualification

### Problem
After lowering `extract_signals_for_identifier`'s `max_group_size` default from 500 to 50 (previous entry), the full-dataset pipeline was **still** OOM-killed. Step-by-step memory profiling (`psutil`-based, not guessing) showed `extract_all_raw_signals(rep)` alone reached 1.83GB RSS and produced **11,498,825** raw signals — the exact count expected under the *old* cap of 500, not the fixed cap of 50.

### Why It Happened
`extract_all_raw_signals`, the top-level function actually used by callers, had its own separate `max_group_size: int = 500` default in its own function signature, independent of `extract_signals_for_identifier`'s default. The previous fix edited only the latter. Calling `extract_signals_for_identifier` directly (as an isolated profiling test did) correctly used 50 and produced the expected 728,509 signals; calling the top-level `extract_all_raw_signals` — the actual production code path — silently fell back to 500.

### What Was Tried
Ran `extract_signals_for_identifier` directly with an explicit `max_group_size=50` argument first, in isolation, to sanity-check the earlier fix — this succeeded and produced the expected ~728K signals, which briefly suggested the fix was working. Only running the *actual* full pipeline entry point (`extract_all_raw_signals`) with memory profiling revealed the discrepancy.

### What Failed and Why
Testing the lower-level function directly instead of the actual call path callers use gave a false sense that the fix was in place — the isolated call bypassed the very default that was still broken. This is a specific instance of a general lesson: verify the function that's actually called in production, not just the function that contains the logic being fixed.

### What Finally Worked
Updated `extract_all_raw_signals`'s own default to 50 to match. Added a regression test (`test_extract_all_raw_signals_default_matches_per_identifier_default`) that asserts the two defaults stay equal via `inspect.signature`, so a future edit to one default can't silently diverge from the other again.

### What Changed in the System
`graph/relationships.py`: `extract_all_raw_signals` default changed 500->50. `tests/test_graph.py`: added the defaults-consistency regression test.

### Guardrail / Evaluation Check
No effect on qualification logic or thresholds — purely closes a gap where a memory-safety parameter had two independent sources of truth.

### Evidence
Before fix: `extract_all_raw_signals(rep)` -> 11,498,825 signals, 1.83GB RSS, process killed shortly after. After fix: matches the 728,509-signal, ~360MB profile measured via the per-identifier function directly.

**Commit:** `fix: extract_all_raw_signals had a stale duplicate max_group_size=500 default that silently undid the earlier fix; add regression test`

**Issue/PR:** (none — single-session fix during Day 2 verification)

---

## Parquet column-load memory spike during batch inference

**Day/date:** Day 3, 2026-08-29

**Area:** Infrastructure (memory) / ML

### Problem
Scoring all 590,540 transactions with the trained XGBoost model (needed to aggregate a mean risk score per pseudo-entity for cluster scoring) was OOM-killed even after loading only the 369 needed feature columns via `pd.read_parquet(path, columns=[...])` — the same pattern that fixed earlier OOMs.

### Why It Happened
`df.memory_usage(deep=True)` on the loaded, column-limited DataFrame reported only ~872MB, but actual process RSS measured with `psutil` right after the same load was ~2.7GB. Reading a parquet file via pandas/pyarrow holds an intermediate Arrow table in memory during decompression and type conversion, on top of the final pandas DataFrame — for this file's size, that transient overhead was roughly 3x the settled DataFrame size, leaving too little headroom for the feature array + XGBoost's own prediction buffers on top.

### What Was Tried
Column-limiting alone (the fix that worked for two earlier OOMs) was applied first and was insufficient here — confirmed by measuring actual RSS with `psutil.Process().memory_info().rss` immediately after the load, rather than trusting `df.memory_usage()`, which does not capture the parquet-read transient.

### What Finally Worked
Switched to streaming the parquet file in row-group batches via `pyarrow.parquet.ParquetFile.iter_batches(batch_size=50000, columns=[...])`, converting and predicting one batch at a time so the full dataset is never held as one in-memory table. Peak memory stayed bounded to one batch's worth of data plus the model.

### What Changed in the System
Batch inference is now the standard pattern for scoring the full dataset with the trained model — kept in the working script for Day 3's cluster-scoring step. No change to the model, its training, or Layer A results.

### Guardrail / Evaluation Check
No change to any modeling or evaluation logic — purely a memory-handling fix for applying an already-trained, already-evaluated model at full-dataset scale.

### Evidence
`df.memory_usage(deep=True)`: 871.6MB. Actual RSS via `psutil` immediately after the same load: 2699.1MB. Batched streaming approach completed successfully across 12 batches of 50,000 rows each, producing risk scores for all 248,038 pseudo-entities (mean 0.183, consistent with the ~3.5% base fraud rate and the model's known false-positive behavior from Layer A).

**Commit:** `fix: stream parquet in row-group batches for full-dataset inference to fix OOM`

**Issue/PR:** (none — single-session fix during Day 3 verification)

---

## temporal_coordination compresses to near-zero under min-max scaling (documented limitation, not fixed)

**Day/date:** Day 3, 2026-08-29

**Area:** Cluster Scoring / Evaluation

### Problem
Running the normalized hybrid score on real full-dataset clusters, `temporal_coordination` came out as ~0.000003-0.0002 for essentially every cluster, including the highest-ranked ones — visually indistinguishable from zero, even though the formula is implemented exactly as specified (Section 7: inverse time-spread, min-max scaled to [0,1]).

### Why It Happened
At least one cluster has member transactions with (near-)identical `transaction_dt`, giving `inverse_spread = 1/(1+0) ≈ 1`, which becomes the max of the min-max scale. Every other cluster's inverse-spread value is comparatively tiny, so min-max scaling compresses nearly all of them toward 0 — a single extreme outlier is setting the scale for the whole population.

### What Was Tried / Current status
Not fixed. Confirmed via the weight-sensitivity check that this does not appear to distort the overall ranking much in practice (`temporal_coordination_up`/`_down` top-20 overlap: 0.95/1.0 — changing this weight barely moves the top-ranked clusters), so it is being left as a **documented, known limitation** rather than patched with an ad hoc rescaling (e.g. percentile-based) that isn't specified anywhere in the canonical docs and would be an unrequested scope addition mid-build.

### What Changed in the System
Nothing — this is intentionally left as-is and documented here plus in the scoring module, so it doesn't get silently rediscovered later or mistaken for a new bug. A real fix (e.g. percentile clipping before min-max, or log-scaling the spread) is a reasonable Day-5-or-later improvement if time allows, not a Day 3 blocker.

### Guardrail / Evaluation Check
Weights still sum to 1, all components still verified in [0,1] (the pytest suite enforces this). No leakage — this is a scaling property of the min-max formula applied to real data, not a threshold-selection issue.

### Evidence
`temporal_coordination` column values for the top-10 scored clusters: 0.000003 to 0.0002, against a component range of [0,1]. Weight-sensitivity overlap for this component: 0.95 (up) / 1.0 (down) at top-20 — i.e., doubling or removing its practical influence barely changes which clusters rank highest.

**Commit:** (documentation only — no code change)

**Issue/PR:** (none — logged as a known limitation during Day 3 verification)

---

## Ring injector dtype errors on real column types

**Day/date:** Day 4, 2026-08-29

**Area:** Synthetic Evaluation (ring injector)

### Problem
`inject_ring_scenario()` raised `TypeError: Invalid value '...' for dtype 'int64'`/`'float64'` when tested against realistic column types: assigning a float time-offset into an integer `transaction_dt` column, and separately assigning a synthetic string value (e.g. `"SYNTH-addr1-101"`) into a numeric `addr1` column.

### Why It Happened
The representative view's columns keep their natural IEEE-CIS dtypes (`transaction_dt` as int-like, `addr1` as float, `device_info` as object/string). The injector was written assuming it could freely assign a float or a string into whatever dtype the target column happened to have — pandas raises rather than silently upcasting in these cases.

### What Was Tried / What Finally Worked
Cast `transaction_dt` to `float64` before writing offset values into it, and cast the target identifier column to `object` dtype before writing the synthetic string value into it — both casts applied only when the scenario actually injects a ring (`ring_size > 0`), preserving the zero-size negative-control scenario as a true no-op (verified by `test_zero_size_ring_is_a_valid_negative_control`, which asserts the output frame is byte-for-byte identical to the input when no ring is injected).

### What Changed in the System
`data/ring_injector.py`: added the two dtype casts, scoped to only run when a ring is actually being injected.

### Guardrail / Evaluation Check
Caught entirely within `scenarios_dev.yaml`-based unit tests, before any real scenario config was run against the full dataset — no `scenarios_test.yaml` involvement, correctly (a static repo-wide guard test now also verifies no file outside the Day 5 evaluation script references `scenarios_test.yaml` at all, and confirms the file doesn't exist yet).

### Evidence
Before fix: `TypeError: Invalid value '25381.61...' for dtype 'int64'` and `TypeError: Invalid value 'SYNTH-addr1-101' for dtype 'float64'`. After fix: all 7 ring-injector tests pass, including determinism, ground-truth correctness, and the negative-control no-op check.

**Commit:** `fix: ring injector dtype errors when injecting float offsets/string values into numeric columns`

**Issue/PR:** (none — single-session fix during Day 4 verification)

---

## SQLite cross-thread audit-log error under FastAPI TestClient

**Day/date:** Day 4, 2026-08-29

**Area:** Database / Infrastructure

### Problem
`tests/test_api.py`'s investigate/approve/reject tests failed with `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread` — the audit-log write inside `/clusters/{id}/investigate` crashed when called through FastAPI's `TestClient`.

### Why It Happened
The audit SQLite connection was created once at `load_state()` time (one thread) but FastAPI's `TestClient` (and FastAPI's real request handling in general) can dispatch a given request's handler on a different thread. SQLite's default `check_same_thread=True` forbids using a connection object across threads.

### What Finally Worked
`sqlite3.connect(db_path, check_same_thread=False)`. This module still only ever issues one `INSERT` (`append_audit_entry`) and one `SELECT` (`get_audit_trail`) — disabling the same-thread check permits calling those two functions from request-handling threads; it does not add any new capability or weaken the INSERT/SELECT-only design.

### What Changed in the System
`backend/audit.py`: `get_connection()` now passes `check_same_thread=False`, with the reasoning documented inline so it isn't mistaken for a careless "just make the error go away" fix later.

### Guardrail / Evaluation Check
No change to what operations are possible against the audit log — still exactly INSERT and SELECT, nothing else. This is purely a threading-compatibility fix for the reference SQLite substitute used in this sandbox (see backend/audit.py's module docstring on the Postgres-vs-SQLite gap).

### Evidence
Before fix: 2 of 7 `tests/test_api.py` tests failed with the cross-thread `ProgrammingError`. After fix: all 7 pass, including a genuine end-to-end investigate -> policy-decision -> audit-write flow (with the LLM call mocked) run through FastAPI's real request-handling path via `TestClient`.

**Commit:** `fix: SQLite check_same_thread=False for audit connection under FastAPI TestClient`

**Issue/PR:** (none — single-session fix during Day 4 verification)

---

## Ring injector card_combo scenarios silently no-op

**Day/date:** Day 5, 2026-08-29

**Area:** Synthetic Evaluation (ring injector) / Graph

### Problem
Running `scripts/day5_final_evaluation.py` (the Day 5 Layer B2 script, the first real use of `card_combo`-type scenarios) crashed with `KeyError: 'card_combo'` inside `graph/relationships.py`'s `extract_all_raw_signals`, which expects to compute `card_combo` itself from `card1/card2/card5/card6` — it is not a real column on the entity representative view at all.

### Why It Happened
`data/ring_injector.py`'s `inject_ring_scenario` treated `scenario['shared_signal']` as a literal column name to write a synthetic value into, for all three signal types uniformly. That works for `device_info` and `addr1` (real columns), but `card_combo` is a *derived* value, recomputed downstream by `graph/relationships.py` from four underlying fields. Even if the injector had written a literal `card_combo` column (rather than crashing), `extract_all_raw_signals()` would have silently discarded it and recomputed `card_combo` fresh from the unmodified `card1/card2/card5/card6` fields — the injected ring would never actually share anything by the time signal extraction ran. The crash was actually the fortunate outcome here; the silent-no-op version would have been worse and harder to notice.

### What Was Tried
First fix attempt considered simply adding a literal `card_combo` column to satisfy the immediate `KeyError`. Recognized before implementing that this would only convert a loud crash into a silent, undetected failure (the injected ring would vanish the moment `extract_all_raw_signals` recomputed the field) — not implemented, in favor of fixing the actual root cause.

### What Finally Worked
For `card_combo` scenarios specifically, `inject_ring_scenario` now writes a shared synthetic value into all four underlying fields (`card1`, `card2`, `card5`, `card6`) for the ring's members, so the injected ring has a genuinely identical 4-tuple — exactly what a real shared card-combination is — that survives `build_card_combo_key`'s downstream recomputation intact. Added a regression test that runs the actual downstream recomputation function against the injector's output and confirms the ring still shares exactly one card_combo value afterward, rather than only checking the injector's own output in isolation.

### What Changed in the System
`data/ring_injector.py`: `card_combo` scenarios now branch to inject into the four underlying card fields instead of a literal `card_combo` column. `tests/test_ring_injector.py`: added `test_card_combo_injection_survives_downstream_recomputation`, which specifically exercises the actual `graph/relationships.build_card_combo_key` function rather than mocking or assuming its behavior.

### Guardrail / Evaluation Check
Caught before any Layer B2 numbers were produced — no synthetic results were computed on the broken version, so nothing needed to be discarded or re-reported. `scenarios_test.yaml` isolation unaffected: this was a bug in the injector logic itself, not a premature read of the test config (the config was already legitimately open per Day 5).

### Evidence
Before fix: `KeyError: 'card_combo'` when running `scripts/day5_final_evaluation.py`. After fix: injected `card_combo` rings verified (via the new regression test) to share exactly one card_combo value after running the real downstream recomputation, and to not collide with any non-ring entity's combo.

**Commit:** `fix: ring injector card_combo scenarios now inject into the underlying card fields, not a nonexistent literal column; add regression test against real downstream recomputation`

**Issue/PR:** (none — single-session fix during Day 5 verification)

---

## Layer B2: single-signal-type rings above ~4 members are systematically undetected (documented limitation, NOT fixed — post-freeze)

**Day/date:** Day 5, 2026-08-29

**Area:** Evaluation / Edge Qualification

### Problem
Running the real, one-time Layer B2 evaluation (`scripts/day5_final_evaluation.py`, `configs/scenarios_test.yaml`) produced cluster_recall = 0.25 (1 of 4 positive scenarios detected): the 3-member tight `device_info` ring was detected perfectly (precision/recall/purity all 1.0), but the 5-member `card_combo`, 9-member `addr1`, and 15-member `device_info` rings were **not detected at all** — zero overlap with any extracted cluster.

### Why It Happened
Traced precisely, not just observed: each test scenario shares exactly ONE signal type (by design, to test generalization across signal types individually). `qualify_edges()`'s minimum-independent-evidence rule (added Day 1, see "Bridge-chaining from percentage-based identifier rarity") requires either 2+ signal types OR a single signal type with `identifier_rarity >= 0.4`. For a synthetic value shared by exactly `ring_size` entities globally (and nowhere else), `identifier_rarity = 1/(1+log1p(ring_size))`. Computed directly: ring_size=3 -> 0.419 (clears the bar), ring_size=5 -> 0.358, ring_size=9 -> 0.303, ring_size=15 -> 0.265 (all below it). **The log-scaled rarity formula makes a larger ring's shared marker look progressively less "rare" and therefore less qualifying — even though a synthetic marker shared by exactly 15 entities and nowhere else in a 248,038-entity population is arguably a *stronger* coordination signal than one shared by 3, not a weaker one.**

### What Was Tried
None — per `DAILY_BUILD_PLAN.md` Day 5 Task 1 ("Freeze — no further changes to thresholds, weights, or detector logic after this point") and this script's own printed reminder, no attempt was made to adjust `SINGLE_SIGNAL_HIGH_RARITY_BAR`, the rarity formula, or the qualification rule in response to this result. This finding is reported as-is.

### What Failed and Why
N/A by design — no fix was attempted post-freeze, deliberately, so this Layer B2 number reflects the actually-frozen system rather than a result tuned after seeing the test set (which would itself be a `scenarios_test.yaml` isolation violation).

### What Finally Worked
Not applicable — this is an honestly reported limitation, not a resolved failure. The real underlying tension: the minimum-independent-evidence rule exists specifically to stop *common, uninformative* single signals (e.g. a shared address-region code held by thousands of unrelated people) from bridge-chaining unrelated entities together. That same log-scaled rarity measure, applied to a *genuinely rare but larger* synthetic ring, penalizes it for being large rather than rewarding it for being exclusive. Distinguishing these two cases would need something beyond raw shared-entity count — e.g. comparing a value's prevalence against what's typical for its *specific* signal type (a shared address code held by 15 people is unremarkable; a shared card_combo held by 15 people is very unusual, since card_combo cardinality is far higher and legitimate collisions of the full 4-tuple are rare) — a design change appropriately deferred to a future iteration, not attempted here.

### What Changed in the System
Nothing in `graph/edges.py`, `graph/scoring.py`, or any threshold. This entry and `EVALUATION_RESULTS.md`'s Layer B2 section are the only changes — pure documentation of a real, diagnosed, frozen-system limitation.

### Guardrail / Evaluation Check
`scenarios_test.yaml` isolation fully honored: opened exactly once, by exactly one script (`scripts/day5_final_evaluation.py`), no tuning followed. This is precisely the isolation discipline the rule exists to protect — a bad number, reported honestly, with no rerun-until-better temptation acted on.

### Evidence
Full Layer B2 output: `ml/artifacts/layer_b2_results.json`. Cluster recall 0.25 (1/4 positive scenarios). When detected, entity precision/recall/purity all 1.0 (the one true positive was clean, not a partial/noisy match). Rarity-vs-ring-size relationship confirmed by direct computation: 3->0.419, 5->0.358, 9->0.303, 15->0.265 against a fixed 0.4 bar.

**Commit:** (documentation only — no code change, by design, per the Day 5 freeze rule)

**Issue/PR:** (none — logged as a genuine, diagnosed, unresolved limitation during Day 5 final evaluation)

---

## External review caught 5 real post-freeze issues (pyarrow, exposure=0.0, frontend/API drift, currency symbol, doc drift)

**Day/date:** post-Day-5, 2026-08-31

**Area:** Infrastructure / API / Frontend / Documentation

### Problem
An external technical review of the delivered zip, run against a genuinely clean environment, found: (1) `pyarrow` missing from `requirements.txt` — 6 tests failed on a clean `pip install`, even though they passed in the dev sandbox where pyarrow had been installed manually earlier; (2) `GET /clusters/{id}` hardcoded `cluster_transaction_value=0.0`, so the API's exposure figure was always zero while the Streamlit views computed the real figure independently — exactly the drift `ARCHITECTURE.md` Section 5a exists to prevent; (3) the frontend reads parquet artifacts and calls backend Python functions directly instead of the documented API-only rendering path; (4) the dashboard displayed exposure with a ₹ symbol despite IEEE-CIS's `TransactionAmt` currency never being confirmed by Vesta/Kaggle — a direct contradiction of this project's own `DATA_STRATEGY.md` philosophy; (5) README claimed "171 passing tests, 16 commits" against an actual 165-passing-plus-6-errors/17-commits reality.

### Why It Happened
(1) happened because the dev sandbox had pyarrow installed from an earlier OOM-debugging session (see the "Recurring pattern" entry above) and `requirements.txt` was never re-synced against it — so every test run "at home" passed, masking the gap. (2) was a known shortcut, explicitly flagged in its own code comment ("kept simple here"), that was never circled back to. (3) was a real, undisclosed architecture deviation. (4) was an unexamined assumption. (5) was a documentation reconciliation that was done once and not re-verified after later commits.

### What Finally Worked
All fixed directly: added `pyarrow==17.0.0` to `requirements.txt` and re-verified 171/171 passing from a genuinely fresh venv; loaded real entity transaction amounts into API state and computed real exposure in `GET /clusters/{id}`; added an explicit `503` with a clear message when the Investigation Agent call fails (e.g. missing API key) instead of an opaque 500; removed the ₹ symbol and added an explicit "currency unconfirmed" note everywhere exposure is displayed; corrected the README's numbers; and — rather than silently refactoring the frontend under time pressure, which risks introducing new untested bugs right before submission — documented the frontend/API architecture deviation explicitly in both frontend files' module docstrings and in a new "Known deviations" README section, matching this project's own standard of disclosure over silent inconsistency.

### What Changed in the System
`requirements.txt`, `backend/api.py` (`get_cluster`, `investigate` endpoints), `frontend/case_detail.py`, `frontend/dashboard.py`, `README.md`.

### Guardrail / Evaluation Check
No detection logic, thresholds, or evaluation results were touched — these were packaging/integration/documentation issues, not modeling ones. Re-ran the full test suite from both the dev environment and a clean venv after every fix.

### Evidence
Clean-venv run after the fix: `171 passed, 1 warning`. Before the fix (as caught externally): `165 passed, 6 errors` due to the missing pyarrow engine.

**Commit:** `fix: pyarrow in requirements, real exposure calculation, explicit 503 on agent failure, remove unjustified currency symbol, reconcile README numbers, document frontend/API architecture deviation`

**Issue/PR:** (none — fixed the same session the external review was received)

---

## Second external review: transaction_risk was mislabeled as a calibrated fraud probability

**Day/date:** post-Day-5, 2026-08-31

**Area:** Financial Semantics / API

### Problem
A second, more careful external review found that the first review's exposure fix (real transaction value instead of `0.0`) had not addressed a deeper issue: `backend/exposure.py`'s parameter was named `cluster_fraud_probability`, and the caller passed `transaction_risk` — a mean of per-transaction XGBoost predicted probabilities across a cluster's members. Averaging per-transaction model scores does not, by itself, produce a calibrated "probability that this coordinated cluster is fraudulent." `EVALUATION_PLAN.md` Section 7 explicitly states "Risk Score != Fraud Probability" — the code was violating its own project's stated discipline even though the surrounding prose respected it.

### Why It Happened
The first review's fix focused narrowly on the reported symptom (exposure always zero) and didn't re-examine whether the *semantics* of the other inputs were correct — a classic case of fixing the specific complaint without re-auditing the surrounding code for the same class of problem.

### What Finally Worked
Renamed the parameter (and its key in the returned dict) from `cluster_fraud_probability` to `model_risk_proxy` throughout `backend/exposure.py`, `backend/api.py`, and both frontend files, and updated the label text to say explicitly this is not a calibrated probability. This is "Option A" (honest relabeling) rather than "Option B" (building and justifying an actually-calibrated cluster-level probability model) — there is no calibration evidence to support Option B, and claiming one without that evidence would be a bigger problem than the mislabeling itself.

### What Changed in the System
`backend/exposure.py` (parameter rename + expanded docstring explaining why), `backend/api.py` and both frontend files (call-site updates), `tests/test_exposure.py` (added a regression test asserting the result never exposes a `cluster_fraud_probability` key and the label explicitly disclaims calibration). Also, in the same pass: a real regression test for the exposure-value bug itself (checking actual nonzero values and cross-referencing an independent computation, not just key presence — the first fix's test was too weak to have caught a regression); an honest implementation note appended to `docs/ARCHITECTURE.md` Section 5a rather than leaving a FINAL/CANONICAL doc describing a frontend architecture that doesn't exist; both exposure inputs now shown explicitly in the UI, not just the final number; mocked provider-dispatch tests for the Anthropic/Groq split added; the fragile hardcoded commit count removed from the README entirely rather than fixed again.

### Guardrail / Evaluation Check
No detection logic touched. This is a labeling/semantics fix in the financial-claim layer, which is exactly where `EVALUATION_PLAN.md` Section 7's discipline is supposed to be enforced — and where it had, in fact, briefly lapsed.

### Evidence
Full suite from a clean venv after this fix: 181 passed (171 prior + 8 new provider-dispatch tests + 2 new regression tests).

**Commit:** `fix: surgical correction pass per second external review - rename cluster_fraud_probability to model_risk_proxy`

**Issue/PR:** (none — fixed the same session the second review was received)

---


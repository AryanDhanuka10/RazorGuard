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


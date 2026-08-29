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

No failures have been recorded yet.

This section should remain unchanged until a genuine failure occurs during the build.


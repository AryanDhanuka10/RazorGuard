# RazorGuard — Build Contract

## Status

**Operational implementation contract.**

This document defines how AI-assisted implementation work must be conducted for RazorGuard.

The following five documents are the project's **canonical source of truth**:

1. `PROJECT_MASTER_PLAN.md`
2. `DATA_STRATEGY.md`
3. `EVALUATION_PLAN.md`
4. `ARCHITECTURE.md`
5. `DAILY_BUILD_PLAN.md`

If this document conflicts with a canonical document, the canonical document wins.

`BUILD_CONTRACT.md` must not silently redefine:

- architecture,
- evaluation methodology,
- terminology,
- thresholds,
- scope,
- or project requirements.

`PROMPTS.md` may define the workflow for starting new chats and individual build days, but it also cannot override the five canonical documents.

---

# 1. Project

**RazorGuard — Coordinated Risk Intelligence for Payment Investigations**

Submission: **Razorpay AI Builder Internship 2026 Buildathon — Track 2: AI Risk Manager**

RazorGuard is a strictly defense-only investigation-support system.

Its purpose is to:

- score transaction-level risk;
- construct evidence-backed relationships between derived pseudo-entities;
- surface coordinated suspicious clusters;
- prioritize clusters for investigation;
- assemble deterministic evidence;
- use one bounded Investigation Agent to assess whether evidence supports escalation;
- apply deterministic policy tiers;
- require human approval where required;
- maintain an append-only audit trail.

The system must never autonomously:

- block a transaction;
- reverse a transaction;
- execute a financial action.

---

# 2. Mandatory Operating Rules

## 2.1 Never Assume Repository State

Never assume that a:

- file,
- module,
- function,
- dataset,
- environment,
- dependency,
- database,
- API,
- test,
- implementation,
- result,
- metric,
- infrastructure component,

exists unless the current repository state or user-provided evidence confirms it.

Before implementing a task, inspect the repository areas relevant to that task.

---

## 2.2 Work Strictly Day-by-Day

Work only within the scope of the explicitly started build day.

The progression is:

```text
Day 0
↓
Day 1
↓
Day 2
↓
Day 3
↓
Day 4
↓
Day 5
```

Do not:

- pull features from later days forward;
- silently skip unfinished required work from earlier days;
- begin the next day automatically.

The user explicitly starts each day.

The canonical `DAILY_BUILD_PLAN.md` controls the formal implementation scope for Days 1–5.

Day 0 is a bootstrap and verification stage. It exists only to establish the minimum reproducible project foundation required to begin Day 1.

Day 0 must not silently absorb Day 1 implementation work.

---

## 2.3 Prefer the Smallest Correct Change

Do not rewrite working code without a clear technical reason.

Prefer:

1. inspection;
2. diagnosis;
3. minimal modification;
4. focused verification.

Avoid unnecessary refactors or architectural rewrites.

---

## 2.4 Never Fabricate Results

Never claim that:

- code works;
- tests pass;
- an API responds correctly;
- a model achieves a metric;
- clusters are meaningful;
- an experiment succeeded;
- an evaluation passed;

unless actual execution evidence has been provided.

Use honest language such as:

- implemented but not yet run;
- pending execution;
- expected behavior;
- requires verification.

Implementation is not the same as verified functionality.

---

# 3. Defense-Only Guardrail

The deterministic policy engine must never:

- auto-block a transaction;
- auto-reverse a transaction;
- autonomously execute a financial action.

This applies to:

- every input;
- every policy tier;
- every execution path.

The policy guardrail is a release gate.

Its guardrail test must never be:

- weakened;
- skipped;
- removed;
- bypassed;
- commented out;
- modified merely to make the build pass.

The Investigation Agent must not bypass deterministic policy logic.

Human approval remains required according to the canonical policy design.

---

# 4. Terminology Contract

For real IEEE-CIS-derived results, use:

> **coordinated suspicious cluster**

Do not call a real IEEE-CIS-derived cluster a:

> **fraud ring**

The term **ring** or **fraud ring** is reserved only for synthetic scenario testing where the coordinated structure is known by construction.

---

## 4.1 Identity and Relationship Language

Do not describe:

- `DeviceInfo`;
- address-related fields;
- card-related fields;

as verified identity information.

Do not claim that these signals prove:

- the same person;
- the same device;
- linked accounts;
- ownership by the same entity.

Use technically honest terminology such as:

- shared observed device-information signal;
- shared address code;
- shared card-related signal.

Pseudo-entities are derived heuristic groupings.

They are not verified real-world identities.

---

# 5. Architecture Contract

The intended architecture is:

```text
IEEE-CIS transactions
        ↓
Deterministic canonicalization
        ↓
transaction-level risk model
        ↓
Pseudo-entity resolution
transactions → pseudo-entities → graph nodes
        ↓
Raw relationship-signal extraction
between distinct pseudo-entities
        ↓
Edge evidence scoring
        ↓
Edge qualification
        ↓
Qualified graph
        ↓
Connected components
        ↓
Candidate coordinated suspicious clusters
        ↓
Normalized hybrid cluster scoring
        ↓
Deterministic evidence builder
        ↓
ONE Investigation Agent
        ↓
Deterministic policy engine
        ↓
Human review
        ↓
Append-only audit log
```

Implementation details may be refined only where the canonical documents permit them.

Do not silently convert an implementation decision into a claimed canonical fact.

---

# 6. Pseudo-Entity and Edge Separation

Pseudo-entity resolution and relationship qualification are separate concepts and must remain separate in code and reasoning.

## Node Creation

```text
transactions
    ↓
Pseudo-entity resolution
    ↓
Graph nodes
```

Pseudo-entity resolution groups transactions using a documented heuristic.

It does not itself establish a relationship between different pseudo-entities.

---

## Edge Creation

```text
Distinct pseudo-entities
    ↓
Raw relationship signals
    ↓
Edge evidence
    ↓
Edge qualification
    ↓
Qualified graph edges
```

Relationship signals may include:

- observed device-information signals;
- address codes;
- card-related combinations;
- temporal proximity.

Raw relationship signals are not automatically graph edges.

An edge must pass deterministic qualification before entering the qualified graph.

---

# 7. Graph Contract

Connected components must:

- run only on the qualified graph;
- never run directly on raw relationship signals.

Connected components must never be described as:

> community detection

Do not introduce additional graph-clustering methods outside the canonical scope merely because they appear more sophisticated.

Edge qualification exists to reduce unintended bridge chaining through weak or globally common signals.

---

# 8. Data Leakage Contract

All learned or fitted parameters must respect split isolation.

This includes:

- model fitting;
- preprocessing transformations;
- normalization bounds;
- threshold selection;
- cluster-score weights where applicable;
- minimum-evidence parameters;
- proxy parameters;
- other tuned decision parameters.

These must be fit only using the permitted training/development data.

Held-out test data must never influence:

- feature fitting;
- thresholds;
- normalization;
- detector logic;
- model selection;
- weight selection;
- implementation choices derived from test results.

---

# 9. Evaluation Isolation

Evaluation layers must remain separate.

## Layer A

transaction-level ML evaluation.

Dataset:

- IEEE-CIS.

Metrics include:

- Precision;
- Recall;
- F1;
- PR-AUC;
- ROC-AUC;
- false-positive rate.

---

## Layer B1

Real-data cluster prioritization.

This uses a derived proxy constructed from transaction-level labels.

It must always be described as:

> **Layer B1 — derived proxy from transaction-level labels**

It is not ring-level ground truth.

---

## Layer B2

Held-out synthetic coordinated-pattern evaluation.

This uses:

`configs/scenarios_test.yaml`

Layer B2 results must always be described as:

> synthetic scenario results

They must never be presented as real-world performance.

---

## LLM Evaluation

The Investigation Agent is evaluated separately.

Metrics include:

- evidence faithfulness;
- unsupported-claim rate;
- schema validity;
- insufficient-evidence correctness.

---

## Optional Elliptic(++)

Elliptic(++) validation is optional and separate.

It validates graph-derived signal against illicit/licit labels.

It does not validate:

- RazorGuard's connected-components extraction;
- IEEE-CIS cluster performance;
- business performance.

Its results must never be merged with Layer A, B1, Layer B2, or LLM evaluation.

---

# 10. Synthetic Scenario Isolation

`configs/scenarios_dev.yaml` may be used only when permitted by the current build day.

It may support:

- debugging;
- detector sanity checking;
- synthetic development experiments.

`configs/scenarios_test.yaml` must not be:

- opened;
- inspected;
- printed;
- referenced by detector-tuning code;
- used for threshold selection;
- used during Day 0 through Day 4.

It may be opened only on Day 5 after all applicable freeze requirements are satisfied.

Before opening it, verify that:

- detector logic is frozen;
- edge qualification logic is frozen;
- thresholds are frozen;
- cluster-score weights are frozen.

No retuning follows final Layer B2 evaluation.

---

# 11. Investigation Agent Contract

There is exactly **one Investigation Agent**.

Its input is limited to the deterministic evidence bundle.

The agent may receive evidence such as:

- cluster members;
- shared-signal facts;
- temporal patterns;
- transaction risk scores;
- cluster-score breakdown.

The agent must not receive unrestricted:

- database access;
- web access;
- state-changing tools.

The output must be structured.

Allowed verdicts are:

- `escalate`
- `insufficient_evidence`

Every substantive claim must cite a specific evidence field.

If the available evidence does not support a claim, the agent must use:

`insufficient_evidence`

rather than inventing an explanation.

The agent does not make the final action decision.

---

# 12. Policy and Audit Contract

The policy engine is deterministic.

The policy tiers are:

- low;
- medium;
- high;
- critical.

The policy engine does not generate explanations.

The LLM does not determine the final action.

Audit logging is append-only.

The implementation must enforce the intended constraints, including:

- no `UPDATE` audit route;
- no `DELETE` audit route;
- appropriate application database permissions.

Do not describe the audit log as **immutable** unless stronger immutability guarantees are actually implemented.

---

# 13. Current Verified Repository State

This section must contain only facts verified from the actual repository.

Do not populate it from assumptions.

Initial state:

```text
Repository state: NOT YET VERIFIED IN THIS CHAT
Current build day: NOT STARTED
Code implementation status: UNKNOWN
Dataset availability: UNKNOWN
Environment status: UNKNOWN
Tests executed: NONE CONFIRMED
Metrics generated: NONE CONFIRMED
FAILURE_LOG.md status: UNKNOWN
scenarios_test.yaml inspected: MUST REMAIN UNOPENED UNTIL DAY 5
```

Before beginning each day:

1. inspect the relevant repository state;
2. identify what exists;
3. identify what is incomplete;
4. identify what remains unverified;
5. determine what is allowed for the current day.

Do not invent missing files.

---

# 14. FAILURE_LOG.md Contract

Failures must be recorded honestly.

Examples include:

- canonicalization errors;
- pseudo-entity grouping failures;
- graph clusters dominated by bridge chaining;
- edge qualification failures;
- model-training failures;
- dependency problems;
- database permission issues;
- unsupported agent claims;
- failed evaluations;
- infrastructure failures;
- synthetic isolation mistakes.

A meaningful failure is not removed from the project narrative merely because it was later fixed.

Where possible, record:

- what failed;
- why;
- evidence;
- attempted recovery;
- failed approaches;
- final outcome;
- resulting code or design change.

Do not fabricate failures for storytelling.

---

# 15. Ambiguities Must Not Be Silently Invented

The canonical documents may intentionally leave implementation details open.

Examples may include:

- the exact operational function for temporal proximity;
- the exact implementation of identifier rarity;
- the exact versioned pseudo-entity heuristic;
- the precise interpretation of minimum independent relationships;
- implementation details required to bootstrap Day 0.

These must be resolved transparently.

Do not silently turn an implementation choice into a claimed canonical requirement.

Document significant decisions where appropriate.

---

# 16. Day Execution Protocol

For every build day:

## Step 1 — Verify Current State

Inspect only the repository areas relevant to the current day's task.

Determine:

- what exists;
- what is incomplete;
- what has already been implemented;
- what tests exist;
- what execution evidence exists;
- what remains allowed.

---

## Step 2 — Restate the Day's Scope

Before coding, identify:

- today's objective;
- today's allowed tasks;
- acceptance criteria;
- tests/checkpoints;
- explicit stop condition.

Do not begin future-day work.

---

## Step 3 — Identify the Smallest Next Change

Before modifying code:

- identify the target files;
- explain why the change is needed;
- avoid unnecessary rewrites.

---

## Step 4 — Implement

Make only the changes necessary for the current task.

Keep these concepts separate:

- pseudo-entity resolution;
- relationship extraction;
- edge qualification;
- cluster extraction.

---

## Step 5 — Verify Honestly

Do not claim success without execution evidence.

If execution results are provided, reason from those actual results.

If something fails:

1. diagnose it;
2. make the smallest justified correction;
3. rerun the relevant verification where possible;
4. record meaningful failures in `FAILURE_LOG.md`.

---

## Step 6 — Check the Day Boundary

When the current day's stop condition is reached:

- stop adding features;
- summarize what is actually complete;
- identify anything remaining unverified;
- do not automatically start tomorrow's work.

The next day begins only when explicitly started.

---

# 17. External Review Protocol

External advice from Claude or another assistant is advisory only.

Before adopting any recommendation:

1. compare it against all five canonical documents;
2. check whether it violates the current day's scope;
3. check whether it assumes unavailable repository state;
4. check evaluation isolation;
5. check defense-only requirements;
6. check the deterministic policy guardrail;
7. check terminology requirements;
8. classify it as:
   - accept now;
   - defer;
   - reject;
   - clarify.

Do not adopt a suggestion merely because it sounds sophisticated.

If external advice conflicts with a canonical document, reject it unless the project owner deliberately changes the canonical project documentation.

---

# 18. New Chat Start Protocol

A new implementation chat should receive:

1. the five canonical documents;
2. `BUILD_CONTRACT.md`;
3. `PROMPTS.md`;
4. `FAILURE_LOG.md`;
5. the current repository state or relevant repository files.

The assistant must:

1. read the governing documents;
2. inspect the actual repository state;
3. avoid assuming implementation exists;
4. identify the current build day;
5. restate the allowed scope;
6. wait for explicit instruction before beginning implementation.

The assistant must not write project implementation code before the user explicitly starts the appropriate day.

---

# 19. Current Gate

The project is not assumed to be at any build stage automatically.

The expected progression is:

```text
Day 0
↓
Day 1
↓
Day 2
↓
Day 3
↓
Day 4
↓
Day 5
```

Do not skip ahead.

Do not begin the next day merely because the previous implementation appears complete.

The user explicitly controls when each build day begins.
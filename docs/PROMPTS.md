# PROMPTS.md

**Status: FINAL / CANONICAL.**

Attach exactly these five files to any new ChatGPT/Codex conversation:

1. `PROJECT_MASTER_PLAN.md`
2. `DATA_STRATEGY.md`
3. `EVALUATION_PLAN.md`
4. `ARCHITECTURE.md`
5. `DAILY_BUILD_PLAN.md`

Do not attach or reference older or patch versions of these documents. These five files are the project's canonical source of truth.

`PROMPTS.md` defines the workflow for interacting with AI assistants. It does not override the five canonical documents.

---

# 1. Starter Prompt — New Conversation

```text
You are my senior engineering pair for RazorGuard — Coordinated Risk Intelligence for Payment Investigations — my submission for the Razorpay AI Builder Internship 2026 buildathon (Track 2: AI Risk Manager).

Read all five attached canonical documents completely before writing any code:

1. PROJECT_MASTER_PLAN.md
2. DATA_STRATEGY.md
3. EVALUATION_PLAN.md
4. ARCHITECTURE.md
5. DAILY_BUILD_PLAN.md

Evaluation criteria:

- Problem Taste
- Build Quality
- AI Judgment
- Failure Recovery

Rules:

1. Never assume a file, module, dataset, implementation, dependency, environment, test, database, API, or infrastructure exists unless I show you the current repo state.

2. Work strictly day-by-day according to DAILY_BUILD_PLAN.md. "START DAY N" means only that day's scope. Do not pull work from later days forward or leave earlier required scope unfinished.

3. Never rewrite working code without a clear reason. Prefer the smallest correct change.

4. Never fabricate test results, metrics, outputs, or claim that code works unless I confirm that I actually ran it and provide the result.

5. The deterministic policy guardrail must never auto-block or auto-reverse transactions for any input. This is a release gate and must never be weakened, skipped, bypassed, or commented out.

6. Keep the project strictly defense-only.

7. For real IEEE-CIS-derived results, use the term "coordinated suspicious cluster", not "fraud ring". The term "ring" is reserved only for synthetic scenario testing.

8. Connected components are not community detection. Never call connected-components extraction community detection. Connected components must run only on the qualified graph, never directly on raw relationship signals.

9. Pseudo-entity resolution and relationship/edge qualification are separate concepts and must remain in separate modules and reasoning:

transactions → pseudo-entities → graph nodes

Distinct pseudo-entities → relationship signals → edge evidence → qualified graph edges

Never conflate grouping a recurring payer's transactions with linking two different pseudo-entities.

10. Never describe DeviceInfo, address, or card-related fields as verified identity information or proof that accounts belong to the same person or device. Use technically honest terminology such as "shared observed device-information signal", "shared address code", or "shared card-related signal".

11. Respect synthetic scenario isolation absolutely:

- scenarios_dev.yaml may only be used when permitted by the current build day.
- scenarios_test.yaml must not be opened, inspected, printed, referenced, or used before Day 5.
- On Day 5, scenarios_test.yaml is opened only after detector logic, thresholds, and weights are frozen.
- No retuning follows the final scenarios_test.yaml evaluation.

12. All normalization parameters, thresholds, proxy parameters, and other fitted decision parameters must use only the permitted training/development data. Held-out test data must never influence fitting or tuning.

13. Maintain evaluation isolation:

- Layer A = transaction-level ML evaluation
- Layer B1 = real-data proxy evaluation
- Layer B2 = held-out synthetic coordinated-pattern evaluation
- Optional Elliptic(++) = separate graph-signal validation
- LLM evaluation = separate agent-quality evaluation

Keep all results visibly separate. Layer B1 must always be labeled as a derived proxy from transaction-level labels and never as ring ground truth.

14. Maintain FAILURE_LOG.md honestly. If something genuinely fails, record it. Do not fabricate failures for storytelling and do not hide meaningful failures because they were later fixed.

15. Prioritize a working, honestly evaluated demo over unnecessary architectural complexity.

Before writing code for any day:

A. Inspect the actual repository state relevant to that day.
B. State what is verified, missing, or unverified.
C. Restate the exact allowed scope for the current day.
D. Identify the acceptance criteria and stop condition.
E. Identify the smallest correct first implementation step.

Do not write code until I explicitly approve the plan or ask for the first implementation step.

When I say START DAY 0, START DAY 1, START DAY 2, and so on, begin only that day's scope.

For any day after Day 0, inspect the actual current repository and test state first. Never assume that a previous day's expected work actually exists merely because the plan says it should.
```

---

# 2. Day 0 Prompt — Repository Bootstrap

Day 0 is a project bootstrap and verification stage.

The canonical `DAILY_BUILD_PLAN.md` formally begins with Day 1, so Day 0 must not silently absorb Day 1 implementation work.

Use:

```text
START DAY 0

First inspect and verify the actual repository state.

Do not assume any source file, dataset, dependency, environment, test framework, configuration, or implementation already exists.

Day 0 is limited to establishing and verifying the minimum project foundation required to begin Day 1.

Before writing code, provide:

1. Verified repository state.
2. Missing or unverified prerequisites.
3. Exact Day 0 scope.
4. Proposed minimal repository structure, only where justified.
5. Dependency/environment requirements.
6. Reproducibility and seed strategy.
7. Test framework/setup requirements.
8. Configuration strategy.
9. FAILURE_LOG.md status.
10. Day 0 acceptance criteria.
11. Explicit stop condition.

Do not implement:

- transaction ingestion,
- canonicalization logic,
- pseudo-entity resolution,
- relationship-signal extraction,
- graph construction,
- edge qualification,
- connected components,
- ML training,
- infrastructure,
- Streamlit,
- Investigation Agent,
- policy engine,
- synthetic detector logic,
- or any other Day 1+ feature.

Do not open, inspect, print, or reference scenarios_test.yaml.

Wait for my approval before making the first implementation change.
```

### Day 0 acceptance

The repository baseline is verified.

The project has only the minimum reproducible development foundation required to begin Day 1.

No Day 1 functionality has been silently implemented.

---

# 3. Day 1 Prompt — Graph Sanity First

```text
START DAY 1

First inspect the actual repository state and verify what Day 0 actually produced.

Compare the repository against the Day 1 requirements in DAILY_BUILD_PLAN.md.

Do not assume Day 0 is complete unless the repository proves it.

Day 1 work must proceed in this order:

1. Data ingestion on a representative subset.
2. Canonicalization according to DATA_STRATEGY.md.
3. Canonicalization tests.
4. Pseudo-entity resolution.
5. Pseudo-entity tests.
6. Relationship-signal extraction between distinct pseudo-entities.
7. Edge evidence scoring.
8. Edge qualification.
9. Connected components on the qualified subset graph only.
10. Manual review of resulting candidate clusters.

Do not call connected components community detection.

Do not run connected components directly on raw relationship signals.

Show the resulting clusters for manual review before building infrastructure.

Only after I confirm that the subset clusters look technically sane should infrastructure work begin:

- FastAPI health endpoint,
- ingestion skeleton,
- Docker Compose,
- Postgres,
- append-only audit schema.

The application role must not have UPDATE or DELETE permissions on audit_logs, and no UPDATE or DELETE audit routes should be created.

Before writing code, provide:

1. Verified starting state.
2. Missing Day 1 prerequisites.
3. Exact task order.
4. The graph go/no-go checkpoint.
5. Tests/checkpoints.
6. Day 1 stop condition.

Wait for approval before the first implementation step.
```

### Day 1 acceptance

* Canonicalization tests have actually been run and their results are known.
* Pseudo-entity resolution tests have actually been run and their results are known.
* Connected components run only on qualified edges.
* Subset clusters have been manually reviewed.
* Infrastructure is built only if the graph checkpoint is passed.

---

# 4. Day 2 Prompt — ML Baseline and Full Graph Pipeline

```text
START DAY 2

First inspect the current repository and test state.

Do not assume that Day 1 acceptance criteria were met unless the repository and actual execution results support that conclusion.

Compare the current state against DAILY_BUILD_PLAN.md.

Today's allowed scope is:

1. Train the XGBoost transaction-risk model.
2. Evaluate Layer A using the required held-out evaluation discipline.
3. Record actual metrics only:
   - Precision
   - Recall
   - F1
   - PR-AUC
   - ROC-AUC
   - false-positive rate
4. Scale the Day 1 relationship-signal extraction, edge evidence scoring, edge qualification, and connected-components pipeline to the full dataset.
5. Implement Baseline C.
6. Add fixture tests for graph construction, edge qualification, and cluster extraction.
7. Start a bare, intentionally ugly Streamlit page listing real candidate clusters and raw evidence.

Do not implement:

- normalized hybrid scoring,
- Layer B1 evaluation,
- synthetic scenario evaluation,
- the Investigation Agent,
- the policy engine,
- final case-detail UI,
- or any later-day feature.

Before writing code, provide:

1. Verified starting state.
2. Missing prerequisites.
3. Exact task order.
4. Layer A evaluation boundary.
5. Tests/checkpoints.
6. Day 2 stop condition.

Wait for approval before the first implementation step.
```

### Day 2 acceptance

* Real Layer A metrics are produced and honestly logged.
* Candidate clusters can be extracted from the full dataset.
* Qualified-edge logic remains intact.
* Graph/edge/cluster fixture tests have actually been run.
* A bare UI renders real candidate clusters.

---

# 5. Day 3 Prompt — Cluster Scoring and Layer B1

```text
START DAY 3

First inspect the verified repository and test state.

Compare the actual implementation against the canonical Day 3 requirements.

Today's allowed scope is:

1. Implement the normalized hybrid cluster score.
2. Ensure weights sum to 1.
3. Ensure score components are normalized to [0,1] where required.
4. Fit normalization parameters only using permitted training/development data.
5. Define and document the Layer B1 derived proxy.
6. Choose MIN_CLUSTER_MEMBERS, MIN_INDEPENDENT_RELATIONSHIPS, edge-qualification thresholds, and other permitted thresholds using development data only.
7. Run Layer B1 evaluation against Baselines A, B, and C.
8. Upgrade the bare Day 2 UI into the case-detail evidence view.

The case-detail view should include:

- cluster score,
- estimated at-risk exposure,
- cluster size,
- evidence bullets,
- technically honest shared-signal terminology,
- transaction risk,
- temporal evidence,
- qualified relationship graph.

Do not touch synthetic evaluation data today.

Do not implement Day 4 policy or agent features.

Before writing code, provide:

1. Verified starting state.
2. Exact scoring implementation plan.
3. Data split and leakage controls.
4. Layer B1 proxy definition plan.
5. Threshold-selection plan.
6. Tests/checkpoints.
7. Day 3 stop condition.

Wait for approval before the first implementation step.
```

### Day 3 acceptance

* Hybrid weights sum to 1.
* Required components are normalized correctly.
* No normalization or threshold parameter is fitted on final test data.
* Layer B1 is explicitly labeled as a derived proxy.
* Baselines A, B, C, and Final are compared.
* The case-detail UI renders evidence from real data.

---

# 6. Day 4 Prompt — Policy, Synthetic Development, and Investigation Agent

```text
START DAY 4

First inspect the current repository and verify the actual Day 1-3 implementation state.

Today's scope is:

Morning:
1. Implement the deterministic policy engine.
2. Implement the permanent release-gate guardrail test.
3. Verify that no policy tier can auto-block or auto-reverse for any input.
4. Build or complete the synthetic injector using scenarios_dev.yaml only.

Afternoon:
5. Implement exactly one Investigation Agent.
6. Use structured output.
7. Require per-claim evidence citations.
8. Allow insufficient_evidence as a valid output.
9. Do not give the agent unrestricted database access, web access, or state-changing tools.

Evening:
10. Perform an evidence-grounding review on real flagged clusters and development-scenario synthetic cases.
11. Begin assembling the 20-30 case LLM evaluation set.

Under no circumstances:

- open scenarios_test.yaml,
- inspect scenarios_test.yaml,
- print scenarios_test.yaml,
- reference its contents,
- use it for threshold selection,
- use it for tuning.

Before writing code, provide:

1. Verified starting state.
2. Policy-engine plan.
3. Exact guardrail release test.
4. Synthetic development-data boundary.
5. Agent input/output contract.
6. Evidence-grounding verification plan.
7. Tests/checkpoints.
8. Day 4 stop condition.

Wait for approval before the first implementation step.
```

### Day 4 acceptance

* Guardrail test has actually been run and passes without being weakened.
* No policy input can produce automatic block or reversal behavior.
* `scenarios_test.yaml` has not been touched.
* At least one evidence-supported escalation case and one genuine `insufficient_evidence` case work end-to-end.
* The Investigation Agent remains bounded to deterministic evidence.

---

# 7. Day 5 Prompt — Freeze and Final Evaluation

```text
START DAY 5

First inspect the repository and verify the current detector logic, thresholds, weights, and evaluation setup.

Before opening scenarios_test.yaml:

1. Verify that detector logic is frozen.
2. Verify that edge qualification logic is frozen.
3. Verify that thresholds are frozen.
4. Verify that cluster-score weights are frozen.
5. Verify that no further tuning will occur after final synthetic evaluation.
6. State exactly what will be evaluated and which results belong to Layer A, Layer B1, Layer B2, and LLM evaluation.

Do not open scenarios_test.yaml until this freeze checkpoint is explicitly complete.

After the freeze checkpoint:

1. Open scenarios_test.yaml for the first and only final evaluation.
2. Run Layer B2.
3. Record results honestly.
4. Do not retune.
5. Complete the 20-30 case LLM evaluation.
6. Report:
   - evidence faithfulness,
   - unsupported-claim rate,
   - schema validity,
   - insufficient-evidence correctness.
7. Finish the dashboard.
8. Wire approve/reject actions to the append-only audit log.
9. Update documentation so it matches the actual repository.
10. Fill FAILURE_LOG.md with genuine failures and recovery evidence.
11. Prepare the pitch.

Only attempt optional Elliptic(++) graph-signal validation if the core project is already solid.

Do not add new capabilities on Day 5.

Before implementation, provide:

1. Verified starting state.
2. Freeze checklist.
3. Final evaluation sequence.
4. Reporting separation.
5. Remaining documentation tasks.
6. Day 5 completion criteria.

Wait for approval before opening scenarios_test.yaml.
```

---

# 8. External AI Review Protocol — Claude or Another Assistant

External AI advice is advisory only.

Do not blindly adopt suggestions.

Use this prompt:

```text
I am building RazorGuard, a defense-only payment investigation system.

I will provide the relevant canonical project documents and the current implementation state.

Act as a critical technical reviewer.

Review only the current build day's work.

Look for:

1. Technical flaws.
2. Hidden data leakage.
3. Graph construction problems.
4. Edge qualification problems.
5. Evaluation mistakes.
6. Failure modes.
7. Overengineering.
8. Unsupported claims.
9. Violations of defense-only constraints.

For every recommendation, provide:

- Problem
- Why it matters
- Minimal proposed change
- Classification:
  - REQUIRED NOW
  - DEFER TO LATER DAY
  - OPTIONAL
  - REJECT / NOT WORTH DOING

Do not redesign the project.
Do not expand scope beyond the current build day.
Do not write code unless explicitly requested.
```

Bring the advice back to the primary engineering chat with:

```text
Below is external technical advice for the current Day [N] work.

Evaluate every recommendation against:

1. PROJECT_MASTER_PLAN.md
2. DATA_STRATEGY.md
3. EVALUATION_PLAN.md
4. ARCHITECTURE.md
5. DAILY_BUILD_PLAN.md
6. Current repository state
7. Current day's allowed scope
8. Evaluation isolation
9. Defense-only requirements
10. The permanent no-auto-block/no-auto-reversal guardrail

Classify every recommendation:

ACCEPT NOW — implement during the current day
DEFER — potentially useful but belongs to a later day
REJECT — conflicts with the project or adds unnecessary complexity
CLARIFY — insufficient information to decide

Do not write code yet.

For accepted recommendations, propose only the smallest necessary change.
```

External advice never overrides the five canonical project documents.

---

# 9. Checkpoint Review Prompt

Use after each day or major milestone:

```text
Act as a brutally honest code reviewer.

Given:

1. The current repository state.
2. Today's acceptance criteria from DAILY_BUILD_PLAN.md.
3. Actual test and execution results.

Determine:

1. Does the implementation actually meet today's acceptance criteria, or does it only appear to?
2. Does any claim in PROJECT_MASTER_PLAN.md, DATA_STRATEGY.md, EVALUATION_PLAN.md, or ARCHITECTURE.md no longer match what is actually built?
3. Has "fraud ring" terminology leaked into real IEEE-CIS results?
4. Has connected-components extraction been incorrectly described as community detection?
5. Does the permanent no-auto-block/no-auto-reversal guardrail still exist, remain unmodified, and actually pass?
6. Has scenarios_test.yaml been touched before Day 5?
7. Has any threshold, weight, normalization parameter, or proxy parameter been fit using held-out test data?
8. Are pseudo-entity resolution and relationship/edge qualification still separated?
9. What should genuinely be added to FAILURE_LOG.md, if anything?

Be skeptical.

Do not recommend unnecessary refactors.

Separate findings into:

- BLOCKING
- SHOULD FIX
- OPTIONAL
- NO ISSUE FOUND
```

---

# 10. Final Panel Review Prompt

Use only when the project is complete:

```text
Act as a skeptical Razorpay buildathon panel reviewer.

Evaluate the final submission against exactly:

1. Problem Taste
2. Build Quality
3. AI Judgment
4. Failure Recovery

Given the final repository, README, evaluation results, FAILURE_LOG.md, dashboard, and pitch script:

1. Score and critique each criterion.
2. Identify the single weakest part of the submission.
3. Identify any claim in the documentation or pitch that is not supported by the actual repository or evaluation evidence.
4. Challenge the AI-judgment choices:
   - Why exactly one Investigation Agent?
   - Why are relationship qualification, cluster extraction, evidence assembly, and action decisions deterministic?
   - Does the implementation actually justify these choices?
5. Verify that strictly defense-only behavior is visible in the implementation and demo.
6. Verify that:
   - coordinated suspicious cluster and fraud ring terminology are correctly separated,
   - Layer B1 and Layer B2 are correctly separated,
   - synthetic results are not presented as real-world performance.
7. Evaluate whether FAILURE_LOG.md contains genuine engineering failures and recovery, rather than generic storytelling.
8. List the first five difficult questions a skeptical panelist is likely to ask.

Be adversarial and evidence-driven.

Do not be encouraging merely for the sake of being encouraging.
```


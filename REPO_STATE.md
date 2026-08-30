# REPO_STATE.md
Updated at the end of the build session (Days 0-5 completed in one continuous session). Populated from actual verification, not assumption, per BUILD_CONTRACT.md Section 13.

## Test suite
171 pytest tests, all passing (`pytest tests/ -q`). Includes the never-weakened policy guardrail test (109 parametrized cases) and multiple regression tests written directly from real bugs found during this build.

## What's real and verified
- Full Day 1-3 pipeline run against the real 590,540-transaction IEEE-CIS dataset (not a sample, not synthetic placeholders): canonicalization, pseudo-entity resolution (248,038 entities), relationship-signal extraction (728,509 signals), edge qualification (6,289 qualified edges), connected-components clustering (3,425 clusters), XGBoost Layer A, normalized hybrid cluster scoring, Layer B1 evaluation.
- Layer B2 run for real, exactly once, against `configs/scenarios_test.yaml` (created and opened by `scripts/day5_final_evaluation.py` only — confirmed by a static repo-wide grep test).
- Policy engine + its 109-case guardrail test.
- FastAPI backend + SQLite audit log, verified in-process via TestClient with the LLM call mocked (real end-to-end investigate -> policy -> audit-write flow).
- Three Streamlit UIs, each actually started and confirmed serving (HTTP 200) against real computed data.
- 12 genuine engineering failures found, diagnosed, and (in 10 of 12 cases) fixed with regression tests, logged honestly in FAILURE_LOG.md as they happened.

## What's honestly NOT verified
1. **Investigation Agent live call.** No `ANTHROPIC_API_KEY` in this sandbox (confirmed by direct env check). `agents/investigate.py`'s prompt construction and response schema validation are tested with mocked/canned responses; the actual model call has never executed. This is the single largest unverified piece of the build.
2. **Docker / Postgres.** No Docker daemon in this sandbox (confirmed: `which docker` fails). `backend/audit.py` substitutes SQLite, with the INSERT/SELECT-only guarantee enforced only at the application layer, not by a real Postgres GRANT as ARCHITECTURE.md Section 7 specifies.
3. **Elliptic(++) validation.** Optional per DATA_STRATEGY.md/EVALUATION_PLAN.md, and never attempted — the Elliptic(++) dataset was never obtained in this session, and the core system's real work took priority.
4. **The 20-30 case LLM evaluation set.** The harness (`agents/eval_harness.py`) is real and tested; a populated result set requires the live agent (see #1).

## Environment
Python 3.12.3, pip 24.0, git 2.43.0. Sandbox is ephemeral — this container's state does not persist to a new chat session. The `razorguard-*.zip` delivered to the user is the actual, complete, current state of the repository, including the `.git` history.

## scenarios_test.yaml isolation
Created and opened exactly once, by `scripts/day5_final_evaluation.py`, on Day 5, after all detector thresholds were frozen. No tuning followed the Layer B2 run — a genuinely bad result (25% cluster recall) was diagnosed and documented, not used to justify reopening graph/edges.py.

## Current build day
Days 0-5 complete, in the sense of "every task in DAILY_BUILD_PLAN.md was attempted and either done for real or explicitly, honestly flagged as blocked." Not complete in the sense of "ready to deploy without further work" — see the four gaps above.

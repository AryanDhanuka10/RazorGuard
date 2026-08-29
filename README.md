# RazorGuard — Coordinated Risk Intelligence for Payment Investigations

Submission for the **Razorpay AI Builder Internship 2026 Buildathon — Track 2: AI Risk Manager**.

Strictly defense-only: this system flags, prioritizes, and escalates coordinated suspicious activity for human review. It never autonomously blocks, reverses, or executes a financial action.

## Status
Day 0 (bootstrap) — in progress. See `REPO_STATE.md` for the verified current state (updated honestly, not assumed).

## Canonical documents
The following, in `docs/`, are the project's source of truth — everything else (including this README) is downstream of them:
1. `docs/PROJECT_MASTER_PLAN.md`
2. `docs/DATA_STRATEGY.md`
3. `docs/EVALUATION_PLAN.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DAILY_BUILD_PLAN.md`

`docs/BUILD_CONTRACT.md` governs how AI-assisted work on this repo is conducted. `docs/PROMPTS.md` defines the chat-workflow convention. Neither overrides the five canonical docs above.

## Layout
```
data/      ingestion, canonicalization, pseudo-entity resolution, synthetic ring injector
ml/        XGBoost transaction risk model (Layer A)
graph/     relationship-signal extraction, edge qualification, connected-components clustering, cluster scoring
agents/    the single Investigation Agent
policy/    deterministic policy engine (4 tiers, human-approval gate)
backend/   API surface + orchestration
frontend/  Streamlit dashboard
configs/   scenarios_dev.yaml (free use Days 1-4) / scenarios_test.yaml (opened once, Day 5 only)
tests/     pytest suite, including the never-weakened policy guardrail test
```

## Setup
```bash
pip install -r requirements.txt
```
Dataset: IEEE-CIS Fraud Detection (Kaggle). Not yet present in this repo — see `REPO_STATE.md` for the current access blocker and how to resolve it.

## Failure log
Genuine build failures and recoveries are recorded honestly in `FAILURE_LOG.md`, per its own contract — never pre-written, never invented for narrative effect.

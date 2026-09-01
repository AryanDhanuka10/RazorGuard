# RazorGuard — Coordinated Risk Intelligence for Payment Investigations

Submission for the **Razorpay AI Builder Internship 2026 Buildathon — Track 2: AI Risk Manager**.

Strictly defense-only: this system flags, prioritizes, and escalates coordinated suspicious activity for human review. It never autonomously blocks, reverses, or executes a financial action — enforced structurally (see `policy/engine.py`), not just by convention.

## Status: Days 0-5 built and verified against real data, with two honestly-documented gaps

171 passing pytest tests (verified from a clean `pip install -r requirements.txt`, not just this dev environment). A commit per completed unit of work, each following real verification against the actual IEEE-CIS dataset (not synthetic placeholders) wherever the canonical docs called for real data — see `git log --oneline` for the current count rather than a number hardcoded here, which drifted out of date at least once already.

**What actually works, verified by running it:**
- Full pipeline: canonicalization → pseudo-entity resolution → relationship-signal extraction → edge qualification → connected-components clustering → XGBoost risk model → normalized hybrid cluster scoring, all run against the real 590,540-transaction IEEE-CIS dataset
- Layer A, B1, and B2 evaluations, all with real, sometimes unflattering numbers (see `EVALUATION_RESULTS.md`) — nothing was re-run until it looked better
- Deterministic policy engine with a 109-case guardrail test proving it can never auto-block or auto-reverse
- FastAPI backend + audit log, verified end-to-end in-process (investigate -> policy decision -> audit write) with the LLM call mocked
- Two Streamlit UIs (a bare Day-2 list and a styled Day-3 case-detail/dashboard view), both actually started and confirmed serving real computed data (HTTP 200)
- A seeded synthetic ring injector with a statically-enforced dev/test isolation guard

**What's honestly incomplete — read before assuming this is production-ready:**
1. **The Investigation Agent's live LLM call has never actually run in this sandbox.** No API key is available here for either supported provider. Code and tests are real for both `anthropic` and `groq` (`agents/investigate.py`, `tests/test_investigate_providers.py`, mocked) — but nobody has seen a real model verdict for a real cluster yet. Set `ANTHROPIC_API_KEY` or (`GROQ_API_KEY` + `RAZORGUARD_LLM_PROVIDER=groq`, Groq has a free tier) and run it for real before trusting its output.
2. **The Postgres path in `backend/audit.py` has never run against a real Postgres server.** No Postgres daemon is available in this sandbox. The dual-backend code (SQLite fallback / real Postgres via `DATABASE_URL`) and `scripts/postgres_setup.sql` (creates the table plus a restricted `razorguard_app` role with `GRANT INSERT, SELECT` only — the actual DB-level guarantee `ARCHITECTURE.md` Section 7 specifies) are real and syntax-checked, and `tests/test_postgres_audit.py` mocks `psycopg2.connect` to verify query shape and parameter binding. That is not the same as proving the real SQL runs against a real server — run `scripts/postgres_setup.sql` against a real free Postgres instance (Neon, Supabase) and re-run the test suite pointed at it before trusting this path.

See `FAILURE_LOG.md` for the genuine engineering failures found along the way (see that file for the current count rather than a number hardcoded here) — including the Day 1 bridge-chaining bug that the architecture's own go/no-go checkpoint was designed to catch, and did.

## Known deviations from the canonical docs (documented, not hidden)
An external technical review of this repo caught these — most are now fixed, the rest are disclosed instead:
1. ~~`pyarrow` was missing from `requirements.txt`~~ — **fixed**. Verified by installing into a genuinely clean venv and running the full suite: 171 passed.
2. ~~`GET /clusters/{id}` hardcoded exposure's transaction value to `0.0`~~ — **fixed**, with a real regression test (`test_cluster_exposure_uses_real_nonzero_transaction_amount`) that independently recomputes the expected value rather than just checking the key exists.
3. ~~The exposure formula's risk input was misleadingly named `cluster_fraud_probability`~~ — **fixed**. `EVALUATION_PLAN.md` Section 7 explicitly distinguishes Risk Score from Fraud Probability, and the code was violating that distinction even though the surrounding prose respected it: the actual input is `transaction_risk`, a mean of per-transaction model scores, not a demonstrated calibrated probability that a cluster is fraudulent. Renamed to `model_risk_proxy` everywhere (`backend/exposure.py`, API, both frontends), with the label now saying explicitly that it is not a calibrated probability.
4. **The frontend (`frontend/dashboard.py`, `frontend/case_detail.py`) reads pipeline artifacts directly instead of calling the API over HTTP**, contradicting `ARCHITECTURE.md` Section 5a's "renders purely from API responses." Rather than silently leaving the canonical doc factually wrong, an implementation note is now appended directly to that section in `docs/ARCHITECTURE.md`, alongside (not replacing) the original design intent — so both what was intended and what was actually built are visible together.
5. ~~The dashboard displayed exposure with a ₹ symbol~~ — **fixed, removed**. IEEE-CIS's `TransactionAmt` currency was never confirmed by Vesta/Kaggle.
6. ~~Exposure's three inputs weren't all visibly shown, only the final figure~~ — **fixed**. Both frontend views now show the model risk proxy, cluster transaction value, and recoverability assumption alongside the result, per `EVALUATION_PLAN.md` Section 7.
7. ~~Groq provider support had no tests~~ — **fixed**. `tests/test_investigate_providers.py` mocks both SDK clients and covers provider dispatch, response-shape parsing for each provider, invalid-provider handling, and malformed/schema-invalid JSON — all without needing a live key. This does not prove the real services behave as mocked; see `agents/investigate.py`'s docstring.
8. `POST /transactions/ingest` and `POST /graph/build` return `501 Not Implemented` — this API is a **read/investigation interface over precomputed batch-pipeline artifacts**, not a live orchestration API. Described that way here rather than implied otherwise.

## Canonical documents
The following, in `docs/`, are the project's source of truth:
1. `docs/PROJECT_MASTER_PLAN.md`
2. `docs/DATA_STRATEGY.md`
3. `docs/EVALUATION_PLAN.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DAILY_BUILD_PLAN.md`

`docs/BUILD_CONTRACT.md` governs how AI-assisted work on this repo is conducted. `docs/PROMPTS.md` defines the chat-workflow convention.

## Layout
```
data/       ingestion, canonicalization, pseudo-entity resolution, time-based splits, ring injector
ml/         XGBoost transaction risk model (Layer A) + artifacts
graph/      relationship signals, edge qualification, clustering, baseline C, hybrid scoring, Layer B1 eval
agents/     evidence builder, structured-output schema, the Investigation Agent, eval harness
policy/     deterministic policy engine (4 tiers, human-approval gate, guardrail test)
backend/    FastAPI API surface, audit log, exposure formula
frontend/   3 Streamlit views: bare list (Day 2), case-detail (Day 3), integrated dashboard (Day 5)
configs/    scenarios_dev.yaml (used Days 1-4) / scenarios_test.yaml (opened once, Day 5)
scripts/    day5_final_evaluation.py -- the ONLY file permitted to open scenarios_test.yaml
tests/      171 pytest tests, including the never-weakened policy guardrail test
```

## Setup
```bash
pip install -r requirements.txt
```
The small precomputed pipeline artifacts needed to serve the dashboard/API are committed under `data/` (see `.gitignore` for exactly which ones — everything else, including the raw dataset, stays out). To regenerate everything from scratch: place `train_transaction.csv` and `train_identity.csv` (IEEE-CIS Fraud Detection, Kaggle) under `data/raw/` and run the pipeline modules in the order described in `docs/DAILY_BUILD_PLAN.md`.

To actually run the Investigation Agent, set an API key first — either:
```bash
export ANTHROPIC_API_KEY=sk-ant-...          # paid
# or, free tier:
export GROQ_API_KEY=gsk_...
export RAZORGUARD_LLM_PROVIDER=groq
```

To use real Postgres instead of the SQLite dev fallback for the audit log: get a free Postgres instance (Neon, Supabase), run `scripts/postgres_setup.sql` once with your admin/owner connection string (it creates the table and a restricted `razorguard_app` role), then set:
```bash
export DATABASE_URL=postgresql://razorguard_app:<password>@<host>/<db>
```
using the restricted role's credentials, not the admin ones.

## Running
```bash
pytest tests/ -v                                    # 171 tests
streamlit run frontend/dashboard.py                  # integrated dashboard
uvicorn backend.api:app --reload                     # API (call backend.api.load_state() first)
python scripts/day5_final_evaluation.py              # re-runs Layer B2 (idempotent -- already run once)
```

## Results
See `EVALUATION_RESULTS.md` for every number this system has produced, each labeled with its dataset, split, and evaluation layer, including the results that don't flatter the system (Baseline B beating the hybrid score on the Layer B1 proxy; 25% cluster recall on Layer B2).

## Failure log
`FAILURE_LOG.md` -- 12 genuine entries, written as they happened, not reconstructed afterward.

# RazorGuard — Coordinated Risk Intelligence for Payment Investigations

Submission for the **Razorpay AI Builder Internship 2026 Buildathon — Track 2: AI Risk Manager**.

Strictly defense-only: this system flags, prioritizes, and escalates coordinated suspicious activity for human review. It never autonomously blocks, reverses, or executes a financial action — enforced structurally (see `policy/engine.py`), not just by convention.

## Status: Days 0-5 built and verified against real data, with two honestly-documented gaps

171 passing pytest tests (verified from a clean `pip install -r requirements.txt`, not just this dev environment). 17 commits, one per completed unit of work, each following real verification against the actual IEEE-CIS dataset (not synthetic placeholders) wherever the canonical docs called for real data.

**What actually works, verified by running it:**
- Full pipeline: canonicalization → pseudo-entity resolution → relationship-signal extraction → edge qualification → connected-components clustering → XGBoost risk model → normalized hybrid cluster scoring, all run against the real 590,540-transaction IEEE-CIS dataset
- Layer A, B1, and B2 evaluations, all with real, sometimes unflattering numbers (see `EVALUATION_RESULTS.md`) — nothing was re-run until it looked better
- Deterministic policy engine with a 109-case guardrail test proving it can never auto-block or auto-reverse
- FastAPI backend + audit log, verified end-to-end in-process (investigate -> policy decision -> audit write) with the LLM call mocked
- Two Streamlit UIs (a bare Day-2 list and a styled Day-3 case-detail/dashboard view), both actually started and confirmed serving real computed data (HTTP 200)
- A seeded synthetic ring injector with a statically-enforced dev/test isolation guard

**What's honestly incomplete — read before assuming this is production-ready:**
1. **The Investigation Agent's live LLM call has never actually run.** This sandbox has no `ANTHROPIC_API_KEY`. Every other piece of `agents/` (evidence bundle construction, structured-output schema validation, the evaluation harness) is real, tested code — but nobody has seen a real model verdict for a real cluster yet. Run `agents/investigate.py` for real with a key before trusting its output.
2. **Docker/Postgres were never stood up.** This sandbox has no Docker daemon. `backend/audit.py` uses SQLite as a documented substitute; the INSERT/SELECT-only guarantee is enforced at the application layer here, not by an actual Postgres role GRANT as `ARCHITECTURE.md` specifies. Apply the real DB-level restriction when deploying against actual Postgres.

See `FAILURE_LOG.md` for 12 genuine engineering failures found and fixed (or, in two cases, diagnosed and honestly left unfixed post-freeze) while building this — including the Day 1 bridge-chaining bug that the architecture's own go/no-go checkpoint was designed to catch, and did.

## Known deviations from the canonical docs (documented, not hidden)
An external technical review of this repo caught these — all are now fixed except #3, which is disclosed instead:
1. ~~`pyarrow` was missing from `requirements.txt`~~ — **fixed**. Verified by installing into a genuinely clean venv and running the full suite: 171 passed.
2. ~~`GET /clusters/{id}` hardcoded exposure's transaction value to `0.0`~~ — **fixed**. Now computed from real entity transaction amounts, matching what the Streamlit views compute.
3. **The frontend (`frontend/dashboard.py`, `frontend/case_detail.py`) reads pipeline artifacts directly instead of calling the API over HTTP**, contradicting `ARCHITECTURE.md` Section 5a's "renders purely from API responses." This is disclosed in both files' module docstrings rather than fixed — routing through real HTTP calls is a reasonable follow-up, not done here, to avoid a late refactor under submission time pressure. Computation itself is still centralized in one place either way (`backend/exposure.py`, `graph/scoring.py`), so numbers can't drift even though the code path differs from the documented one.
4. ~~The dashboard displayed exposure with a ₹ symbol~~ — **fixed, removed**. IEEE-CIS's `TransactionAmt` currency was never confirmed by Vesta/Kaggle; showing any currency symbol was an unjustified assumption, which this project's own `DATA_STRATEGY.md` explicitly argues against doing.
5. `POST /transactions/ingest` and `POST /graph/build` return `501 Not Implemented` — this API is a **read/investigation interface over precomputed batch-pipeline artifacts**, not a live orchestration API. Described that way here rather than implied otherwise.

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
Place `train_transaction.csv` and `train_identity.csv` (IEEE-CIS Fraud Detection, Kaggle) under `data/raw/`. Run the pipeline scripts in `data/`, `graph/`, and `ml/` in the order described in `docs/DAILY_BUILD_PLAN.md` to regenerate the parquet artifacts under `data/` and `ml/artifacts/` -- these are gitignored (large/derived) and must be regenerated locally.

To actually run the Investigation Agent, set an API key first — either:
```bash
export ANTHROPIC_API_KEY=sk-ant-...          # paid
# or, free tier:
export GROQ_API_KEY=gsk_...
export RAZORGUARD_LLM_PROVIDER=groq
```

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

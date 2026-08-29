# REPO_STATE.md
**Populated only from actual verification performed in this session — no assumptions, per BUILD_CONTRACT.md Section 13.**

## Environment (verified by direct execution)
- Python 3.12.3, pip 24.0, git 2.43.0 — all present and working.
- `pandas`, `pyyaml`, `pytest` installed and import successfully.
  - Actual resolved versions in this sandbox: pandas 3.0.2, pyyaml 6.0.3, pytest 9.1.1 — these differ from the pins in `requirements.txt` (which target the versions used when this file was drafted, e.g. pandas 2.2.2). **This sandbox is ephemeral and is not the environment the real 5-day build will run in** — when you set up the real project environment (locally or in Claude Code), re-resolve and lock actual versions there; don't assume this sandbox's resolved versions are canonical.
- `xgboost`, `fastapi`, `networkx`, `streamlit`, Docker: **not installed/verified yet** — out of Day 0 scope; DAILY_BUILD_PLAN.md brings these in on Day 1 (infra, after the Step 5 checkpoint) and Day 2.

## Dataset access (verified by direct execution — this is a real blocker, not a formality)
- `kaggle.com` is **not reachable from this sandbox** — confirmed via direct request, blocked by the sandbox's own egress policy (`x-deny-reason: host_not_allowed`), not a Kaggle-side error.
- **Consequence: the IEEE-CIS Fraud Detection dataset cannot be downloaded from within this chat's code-execution environment.** Day 1 cannot actually begin (ingestion needs the real CSVs) until the dataset is available to whatever environment does the work. Two ways forward:
  1. Download `train_transaction.csv`/`train_identity.csv` (and test equivalents) from Kaggle yourself and upload them here — I can then work with them directly in this chat.
  2. Do Day 1 onward in an environment with real internet access (your own machine, or Claude Code) where `kaggle datasets download` or the Kaggle API can actually reach kaggle.com.
- Elliptic(++) is optional/secondary (DATA_STRATEGY.md Section 3) — not needed for Day 0/1, same access constraint would apply if/when it's attempted.

## Repository structure (created this session)
```
razorguard/
  data/ ml/ graph/ agents/ policy/ backend/ frontend/  <- empty, per ARCHITECTURE.md Section 2 component boundaries
  configs/                                              <- empty; scenarios_dev.yaml / scenarios_test.yaml do NOT exist yet
  tests/                                                <- empty
  docs/                                                  <- the 7 canonical/contract docs, copied in verbatim
  FAILURE_LOG.md                                        <- template only, no entries (correct — none have occurred)
  requirements.txt, .gitignore, README.md
```

## Current build day
**Day 0 (bootstrap) — in progress.** Day 1 has not started. No detection logic, no models, no API, no DB, no UI exist.

## scenarios_test.yaml
Does not exist. Nothing to isolate yet. Isolation rule is understood and will be enforced once it's created (Day 5 only, per DATA_STRATEGY.md Section 5 / BUILD_CONTRACT.md Section 10).

## Tests executed
None yet — nothing to test until Day 1 ingestion/canonicalization code exists.

## Metrics generated
None.

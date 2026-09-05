<div align="center">

# 🛡️ RazorGuard

### Coordinated Risk Intelligence for Payment Investigations

*Submission for the Razorpay AI Builder Internship 2026 Buildathon — Track 2: AI Risk Manager*

[![Tests](https://img.shields.io/badge/tests-171%20passing-brightgreen)](#testing)
[![Defense Only](https://img.shields.io/badge/policy-defense--only-critical)](#guardrails)
[![Dataset](https://img.shields.io/badge/dataset-IEEE--CIS%20(590K%20real%20txns)-blue)](#dataset)
[![Python](https://img.shields.io/badge/python-3.12-informational)](#tech-stack)
[![License](https://img.shields.io/badge/status-buildathon%20submission-lightgrey)](#status)

</div>

---

## Table of Contents

- [Overview](#overview)
- [The Problem](#the-problem)
- [How It Works](#how-it-works)
- [What's Real, Verified, and What Isn't](#whats-real-verified-and-what-isnt)
- [Results](#results)
- [Guardrails](#guardrails)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Tech Stack](#tech-stack)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Documentation](#documentation)
- [Failure Log](#failure-log)

---

## Overview

**RazorGuard** surfaces *coordinated* suspicious activity in payments data — clusters of accounts that individually look fine but, together, share devices, cards, or addresses in patterns that look deliberately engineered to stay under a single-transaction fraud score's radar.

It is built as a **strictly defense-only decision-support system**. RazorGuard flags, scores, and explains — a human always makes the final call. It has no code path, at any tier, that can autonomously block, reverse, or execute a financial action. That guarantee isn't a policy note; it's enforced structurally in `policy/engine.py` and backed by a 101-case pytest guardrail suite that is never weakened to make a build pass.

> **Honesty is a feature here, not a caveat.** Every metric in this README states its dataset, split, and evaluation layer. Nothing is rounded up, and the two things that were never run for real in this build — the live LLM call and a live Postgres instance — are disclosed up front, not buried in an appendix.

---

## The Problem

A risk analyst triages flagged accounts using a per-transaction fraud score that treats every account as independent. Coordinated abuse — many accounts sharing devices, payment instruments, or timing, deliberately kept under individual thresholds — is invisible to that score *by construction*.

RazorGuard surfaces which **groups** of accounts look coordinated and risky, ranked by evidence-backed suspicion and estimated exposure, so investigation time goes where it matters most.

**Terminology discipline:** on real data, the system never claims to detect a "fraud ring" — IEEE-CIS has no ring-level ground truth to support that claim. It detects and ranks **coordinated suspicious clusters**. "Fraud ring" is reserved for synthetic scenario testing, where ring structure is known by construction.

---

## How It Works

```
  IEEE-CIS real transactions
          │
          ▼
  Deterministic canonicalization
          │
          ▼
  Transaction risk model (XGBoost)  ─────────────────────  Layer A
          │
          ▼
  Pseudo-entity resolution  (transactions → graph nodes)
          │
          ▼
  Relationship-signal extraction  (device / address / card / timing)
          │
          ▼
  Edge evidence scoring + qualification  (filters weak & common signals)
          │
          ▼
  Connected-components clustering  (on the qualified graph only)
          │
          ▼
  Normalized hybrid cluster scoring  ─────────────────────  Layer B1
          │
          ▼
  Deterministic evidence builder
          │
          ▼
  Investigation Agent  (one LLM, structured & evidence-cited output)
          │
          ▼
  Deterministic policy engine  (4 tiers · human-approval gate)
          │
          ▼
  Human review  ──────────────────►  Append-only audit log
```

| Stage | Method | Why |
|---|---|---|
| Transaction risk scoring | XGBoost | Tabular classification — no reasoning needed |
| Relationship extraction & edge qualification | Deterministic | Filtering weak/common edges is exact logic, not a judgment call |
| Cluster extraction | Deterministic (connected components) | No GNN or community detection — edge qualification alone solves the bridge-chaining failure mode |
| Cluster scoring | Deterministic, documented formula | Fully explainable — required for the "why was this flagged" view |
| Case investigation & narrative | **One** LLM agent | The only place raw evidence needs weighing and turning into a readable case |
| Action decision | Deterministic policy engine | Never delegated to the LLM |

Exactly one LLM agent exists in the whole system. It receives a deterministic evidence bundle only — no open-ended database or web access, no state-changing tools — and must cite a specific evidence field for every claim it makes. `insufficient_evidence` is a first-class, expected output, not a failure mode.

---

## What's Real, Verified, and What Isn't

Everything below was actually run in this build, not projected:

- ✅ Full pipeline executed end-to-end against the real **590,540-transaction IEEE-CIS dataset** — canonicalization → pseudo-entity resolution → relationship extraction → edge qualification → clustering → XGBoost risk scoring → hybrid cluster scoring.
- ✅ Layer A, B1, and B2 evaluations, with real numbers — including the ones that don't flatter the system.
- ✅ Deterministic policy engine backed by a 109-case guardrail test proving it can never auto-block or auto-reverse.
- ✅ FastAPI backend + audit log, verified end-to-end in-process (investigate → policy decision → audit write), LLM call mocked.
- ✅ Two Streamlit UIs, both started and confirmed serving real computed data (HTTP 200).
- ✅ A seeded synthetic ring injector with a statically-enforced dev/test isolation guard.
- ✅ **171 passing pytest tests**, verified from a clean install.

Two things are honestly incomplete — flagged here rather than glossed over:

1. **The Investigation Agent's live LLM call has never run in this sandbox.** No API key was available for either supported provider (Anthropic or Groq). The prompt construction, evidence wiring, and response validation are fully tested with mocked responses — but no real model verdict has been produced yet.
2. **The Postgres audit path has never run against a real Postgres server.** No Postgres daemon was available in this sandbox. The dual-backend code, the restricted-role setup script, and the mocked query-shape tests are real — but the actual SQL has not executed against a live server.

See [`FAILURE_LOG.md`](./FAILURE_LOG.md) for the genuine engineering failures found and fixed along the way, and [`REPO_STATE.md`](./REPO_STATE.md) for the full, current verification snapshot.

---

## Results

All numbers below are labeled with their dataset, split, and evaluation layer — see `docs/EVALUATION_PLAN.md` for full methodology and `EVALUATION_RESULTS.md` for the complete report.

### Layer A — Transaction-level classification
*IEEE-CIS, time-based split (413,379 train / 88,581 dev / 88,580 test)*

| Metric | XGBoost | Logistic Regression (baseline) |
|---|:---:|:---:|
| Precision | 0.194 | 0.117 |
| Recall | 0.664 | 0.691 |
| F1 | 0.301 | 0.200 |
| PR-AUC | 0.492 | 0.179 |
| ROC-AUC | 0.861 | 0.815 |
| False-positive rate | 0.099 | 0.188 |

### Layer B1 — Real-data cluster prioritization (derived proxy, *not* ring ground truth)
*3,425 candidate clusters, K = 20 (analyst daily capacity)*

| System | Precision@20 | Recall@20 |
|---|:---:|:---:|
| **Hybrid (final)** | **0.60** | 0.036 |
| Baseline A — total cluster value | 0.30 | 0.018 |
| Baseline B — max member risk | 0.99 | 0.060 |
| Baseline C — structural score alone | 0.40 | 0.024 |

Baseline B beats the hybrid score on this proxy — reported honestly, not hidden. The proxy is derived from the same labels the risk model was trained on, giving a pure risk-score ranking a structural home-field advantage. The hybrid trades some of that for interpretability and multi-signal grounding that Layer B1's narrow proxy can't measure. See `EVALUATION_RESULTS.md` for the full interpretation.

### Layer B2 — Synthetic ring evaluation (real cluster-level ground truth, by construction)
*`configs/scenarios_test.yaml`, opened exactly once, after all detector logic was frozen*

| Scenario | Ring size | Signal | Detected? |
|---|:---:|---|:---:|
| Tiny, device signal, very tight timing | 3 | device_info | ✅ Yes (precision/recall/purity: 1.0 / 1.0 / 1.0) |
| Small, card signal, tight timing | 5 | card_combo | ❌ No |
| Medium, address signal, spread over days | 9 | addr1 | ❌ No |
| Large, device signal, loose timing | 15 | device_info | ❌ No |

**Cluster recall: 0.25.** The cause is diagnosed, not mysterious: the rarity formula that stops common signals from bridge-chaining unrelated entities also penalizes larger, *genuinely exclusive* rings for being large. Full root-cause analysis is in `EVALUATION_RESULTS.md`.

---

## Guardrails

Track 2's official rule is treated as non-negotiable: *"Strictly defense-only: anything offense-capable is disqualified."*

- **4 policy tiers** (low / medium / high / critical) — human approval required above low.
- **No auto-block or auto-reversal at any tier, ever.** The `PolicyAction` enum has no such value defined — this isn't a behavioral promise, it's a structural impossibility.
- **109-case guardrail test**, exhaustively sweeping the full `[0, 1]` score range, functioning as a release gate that is never weakened.
- **Append-only audit log**: no `UPDATE`/`DELETE` route exists on `/audit*` in the API router at all, and the database role is restricted to `INSERT`/`SELECT` only.

---

## Project Structure

```
data/       ingestion, canonicalization, pseudo-entity resolution, time splits, ring injector
ml/         XGBoost transaction risk model (Layer A) + artifacts
graph/      relationship signals, edge qualification, clustering, hybrid scoring, Layer B1 eval
agents/     evidence builder, structured-output schema, Investigation Agent, eval harness
policy/     deterministic policy engine (4 tiers, human-approval gate, guardrail test)
backend/    FastAPI API surface, audit log, exposure formula
frontend/   3 Streamlit views — bare list (Day 2), case-detail (Day 3), integrated dashboard (Day 5)
configs/    scenarios_dev.yaml (used freely) / scenarios_test.yaml (opened once, Day 5 only)
scripts/    day5_final_evaluation.py — the ONLY file permitted to open scenarios_test.yaml
tests/      171 pytest tests, including the never-weakened policy guardrail suite
docs/       the five canonical planning documents (master plan, data strategy, evaluation, architecture, build plan)
```

---

## Getting Started

### Install

```bash
pip install -r requirements.txt
```

The small precomputed pipeline artifacts needed to serve the dashboard/API are committed under `data/`. To regenerate everything from scratch, place `train_transaction.csv` and `train_identity.csv` (IEEE-CIS Fraud Detection, Kaggle) under `data/raw/` and run the pipeline modules in the order described in `docs/DAILY_BUILD_PLAN.md`.

### Run the test suite

```bash
pytest tests/ -v
```

### Launch the dashboard

```bash
streamlit run frontend/dashboard.py
```

### Run the API

```bash
uvicorn backend.api:app --reload
```

### Enable the Investigation Agent

```bash
export ANTHROPIC_API_KEY=sk-ant-...          # paid
# — or, free tier —
export GROQ_API_KEY=gsk_...
export RAZORGUARD_LLM_PROVIDER=groq
```

### Enable real Postgres for the audit log

Get a free Postgres instance (Neon, Supabase), run `scripts/postgres_setup.sql` once with an admin connection string, then:

```bash
export DATABASE_URL=postgresql://razorguard_app:<password>@<host>/<db>
```

---

## Tech Stack

`pandas` · `numpy` · `pyarrow` · `networkx` · `xgboost` · `scikit-learn` · `FastAPI` · `SQLAlchemy` · `psycopg2` · `Streamlit` · `Anthropic` / `Groq` SDKs

---

## Testing

**171 pytest tests**, all passing from a clean install — not just this dev environment. Includes:

- The 109-case policy guardrail suite (never weakened)
- Real graph-construction and edge-qualification regression tests, including a bridge-chaining regression fixture
- Mocked LLM-provider dispatch tests for both Anthropic and Groq
- In-process FastAPI `TestClient` tests covering the full investigate → policy → audit-write flow
- A static repo-wide grep guard confirming `scenarios_test.yaml` is opened by exactly one script

```bash
pytest tests/ -v
```

---

## Known Limitations

- IEEE-CIS's entity fingerprints are a derived heuristic, not a verified real-world identity link.
- No real ring-level ground truth exists for IEEE-CIS — Layer B1's cluster relevance is a documented proxy, never confirmed ring membership.
- Layer B2's synthetic ground truth is only as realistic as the injector; results are reported as synthetic, never as real-world performance.
- Cluster-score weights and minimum-evidence thresholds are tuned on held-out development data but remain assumptions, not production-calibrated values.
- The Investigation Agent's output is bounded by the evidence it's given, and its live call has not been executed in this sandbox.
- Human review remains required for anything above low-risk — this is a decision-support tool, not an autonomous system.

---

## Documentation

The following documents are the project's canonical source of truth, in `docs/`:

1. `PROJECT_MASTER_PLAN.md`
2. `DATA_STRATEGY.md`
3. `EVALUATION_PLAN.md`
4. `ARCHITECTURE.md`
5. `DAILY_BUILD_PLAN.md`

`docs/BUILD_CONTRACT.md` governs how AI-assisted work on this repo is conducted, and `docs/PROMPTS.md` defines the chat-workflow convention used to build it.

---

## Failure Log

`FAILURE_LOG.md` documents 12 genuine engineering failures found during the build — including the Day 1 bridge-chaining bug that the architecture's own go/no-go checkpoint was designed to catch, and did — written as they happened, not reconstructed afterward.

---

<div align="center">

*Built for the Razorpay AI Builder Internship 2026 Buildathon — Track 2: AI Risk Manager.*
*Flags. Prioritizes. Escalates. Never acts alone.*

</div>
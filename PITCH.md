# RazorGuard — 5-Minute Pitch Script

Per `DAILY_BUILD_PLAN.md` Day 5 Task 7: two scenarios, one real failure and recovery, honest metrics, explicit limitations. This is a script to record yourself delivering — I can't produce the video itself, but everything below is grounded in what's actually in this repo.

## 0:00-0:40 — The problem and what RazorGuard is
"Coordinated fraud rarely looks like one bad transaction — it looks like several seemingly-unrelated accounts sharing subtle signals: a device, an address code, a card pattern. RazorGuard finds those coordinated clusters in real IEEE-CIS payments data, scores them, and routes them to a human — it never blocks or reverses anything itself. That's not a design choice we get to reconsider; it's the sourced Track 2 rule, enforced structurally in our policy engine with a 109-case test that would fail if anyone ever added an auto-block path."

## 0:40-1:30 — Architecture in one breath
Walk through the pipeline diagram in `ARCHITECTURE.md` Section 1: canonicalize real data → resolve pseudo-entities → extract relationship signals → **qualify edges** (the step that matters most) → connected components → hybrid cluster score → Investigation Agent → deterministic policy → human approval → append-only audit log.

## 1:30-2:30 — Scenario A: a flagged cluster
Open the dashboard (`frontend/dashboard.py`), pick the highest-scoring real cluster. Show the score breakdown (5 components, all normalized [0,1]), the estimated exposure (explicitly labeled — never "loss prevented"), and the evidence bullets in approved language ("share an observed device-information signal," never "same device").
**Honest caveat to say out loud:** "The live agent verdict for this exact cluster hasn't been generated in front of you before this recording — wire up your API key and this button produces a real cited verdict; we verified the entire pipeline up to that call with the LLM response mocked."

## 2:30-3:00 — Scenario B: insufficient evidence
Pick a low-scoring cluster near the qualification boundary. Explain: `insufficient_evidence` is a first-class output, not a failure mode — the agent is built to say "not enough here" rather than escalate to seem useful.

## 3:00-4:15 — One real failure and recovery (this is the strongest material — use it)
**Tell this one exactly, it's true:** "On Day 1, our own go/no-go checkpoint did its job. A 15,000-entity subset run showed 99% of raw signals qualifying as edges, and 12,885 of 15,000 entities collapsing into a single connected component — textbook bridge-chaining, not real coordination. We traced it to a percentage-of-population rarity formula that couldn't distinguish 'common' from 'rare' for low-cardinality fields like address codes — a value held by 16,000 people is only 6.6% of a quarter-million-entity population, so no percentage cutoff could catch it. We replaced it with a log-scaled absolute-count formula and added a minimum-independent-evidence rule. Qualified edges dropped from 1.4 million to about 1,000, and the largest cluster went from 12,885 down to 7 — with manual inspection confirming those 7 genuinely shared a card and address combination."
Then, briefly, the harder one: "On Day 5, after freezing all thresholds, our synthetic evaluation showed we only detect 1 of 4 injected rings — and we traced that precisely too: our own rarity formula, tuned to stop bridge-chaining, penalizes *larger* genuine rings for looking less 'rare.' We didn't go back and retune after seeing the test set — that would have defeated the point of freezing. We're reporting it as a real, diagnosed limitation."

## 4:15-4:45 — Honest metrics, fast
- Layer A: XGBoost PR-AUC 0.49 vs. logistic baseline's 0.18.
- Layer B1: hybrid beats value-sort 2x, but **loses to a pure risk-score ranking** on this proxy — say why (the proxy shares XGBoost's own training signal).
- Layer B2: 25% cluster recall, with a precise root cause, not a shrug.

## 4:45-5:00 — Close
"Every number in this pitch has a dataset, a split, and a layer label behind it in `EVALUATION_RESULTS.md`. Two things are honestly unfinished: the live agent call needs an API key we didn't have while building, and Postgres's DB-level permission grant needs to be applied at deployment — SQLite stood in during development. Everything else in this repo, we ran."

---
**Note on this document:** this script was written before any human has recorded it, based entirely on what's actually in this repository (git log, `FAILURE_LOG.md`, `EVALUATION_RESULTS.md`) as of the last commit. Update the "Honest caveat" lines above if you run the live agent for real before recording — replace them with what actually happened.

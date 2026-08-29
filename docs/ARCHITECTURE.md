# ARCHITECTURE.md
**Status: FINAL / CANONICAL. Self-contained.**

## 1. Data flow diagram

```
                         REAL DATA
        IEEE-CIS transactions          Elliptic(++) graph (optional,
                |                       only if core is finished)
                v                              |
   canonicalization (deterministic)             v
                |                    graph-based illicit-activity
                v                    signal validation (separate
     transaction risk model (XGBoost)  notebook, own report section)
                |
                v
   pseudo-entity resolution: transactions -> pseudo-entities
   (deterministic heuristic; pseudo-entities = graph NODES,
   kept explicitly separate from the relationship logic below)
                |
                v
   inter-entity relationship signal extraction (raw shared
   signals BETWEEN distinct pseudo-entities: device-info signal,
   address code, card-related combination, temporal proximity)
                |
                v
   edge evidence scoring (identifier rarity + independent-signal
   count + temporal proximity) -> edge qualification (weak/
   globally-common edges filtered — thresholds fit on dev split only)
                |
                v
   candidate cluster extraction via connected components, run
   ONLY on the qualified graph (deterministic — this is NOT
   community detection; no Louvain/Leiden/label-propagation is
   implemented in this project; edge qualification is what
   prevents bridge-chaining through weak/common shared signals)
                |
                v
   normalized hybrid cluster scoring (weights sum to 1, all
   components in [0,1], parameters fit on train/dev only)
                |
                v
   deterministic evidence builder
                |
                v
   Investigation Agent (ONE LLM agent, structured output,
   evidence-cited, evaluated per EVALUATION_PLAN.md Section 5)
                |
                v
   deterministic policy engine (4 tiers, human-approval gate,
   defense-only — sourced official Track 2 rule, never relaxed)
                |
                v
   human review  --------->  append-only audit log (enforced)
```

**Terminology note (binding for all code, docs, and UI copy):** outputs are "coordinated suspicious clusters" everywhere real IEEE-CIS data is involved. "Fraud ring" is used only in synthetic-scenario contexts, where ring structure is known by construction.

## 2. Component boundaries

| Component | Owns | Does not own |
|---|---|---|
| `data/` | Ingestion, canonicalization, pseudo-entity fingerprinting, synthetic ring injector (with dev/test config isolation) | Any modeling logic |
| `ml/` | XGBoost training/inference (Layer A) | Graph construction, decisions |
| `graph/` | Pseudo-entity node resolution, relationship-signal extraction, edge evidence scoring + qualification, connected-components cluster extraction (on the qualified graph only), cluster scoring | Investigation reasoning, policy |
| `agents/` | The single Investigation Agent, its read-only tools, prompt, structured-output schema | Any state-changing action |
| `policy/` | Deterministic tier logic, human-approval gating | Any language generation |
| `backend/` | API surface, orchestration across the above | Business-logic duplication |
| `frontend/` | Streamlit dashboard (built from Day 3 onward, not deferred to the end) | Any decision logic |

## 3. API surface
`POST /transactions/ingest`, `POST /graph/build`, `GET /clusters`, `GET /clusters/{id}`, `POST /clusters/{id}/investigate` (triggers the Investigation Agent), `GET /cases`, `GET /cases/{id}`, `POST /cases/{id}/approve`, `POST /cases/{id}/reject`, `GET /metrics`, `GET /health`. **No `PUT`/`DELETE /audit*` route exists at all** — absent from the router by design, not merely unused.

## 4. Investigation Agent — contract
**Input:** deterministic evidence bundle only — cluster members, shared-identifier facts, temporal pattern, transaction risk scores, cluster score breakdown. Nothing else.
**Output (structured):** verdict (`escalate` / `insufficient_evidence`), confidence, evidence-grounded bullet explanation, a per-claim citation to a specific evidence field.
**Tools:** read-only queries over the already-assembled evidence bundle. No open-ended database or web access. No state-changing tools of any kind.
**Hard rule:** no claim without a citation; `insufficient_evidence` is a first-class, expected output, not a failure mode.
**Evaluation hook:** every production investigation is logged into a review pool so the 20-30 case evaluation set (EVALUATION_PLAN.md Section 5) is drawn from real usage, not only hand-picked examples.

## 5. Cluster scoring
See PROJECT_MASTER_PLAN.md Section 7 for the exact normalized formula, component definitions, and the minimum-evidence configuration rule. Runs only on clusters extracted from the qualified graph (Section 1).

## 5a. Frontend — case-detail/evidence view
Full mockup spec in PROJECT_MASTER_PLAN.md Section 11a. Architecturally: `frontend/` renders this view purely from `GET /clusters/{id}` and `GET /cases/{id}` API responses — it computes nothing itself, including score-to-percentage or exposure formatting, which stay in `backend/`/`graph/` so the displayed numbers can never drift from what was actually computed and logged. Built incrementally starting Day 2-3 (DAILY_BUILD_PLAN.md), not assembled for the first time during Day 5 integration.

## 6. Policy guardrails
4 tiers (low / medium / high / critical). Human approval required above low. No auto-block or auto-reversal at any tier, ever — this is the sourced official Track 2 disqualification rule, not a discretionary design note. The policy engine is implemented as a pure function (`policy/engine.py`) with a pytest suite that functions as a release gate: for any input, the function must never return an auto-block/auto-reversal action. This test is never weakened, skipped, or modified to make a build pass.

## 7. Audit logging — enforced
- No `UPDATE`/`DELETE` route on `/audit*` exists in the API router (Section 3).
- The database role the application uses has `INSERT`/`SELECT` only on `audit_logs` — no `UPDATE`/`DELETE` grants.
- Hash-chaining (`previous_event_hash`/`event_hash`) was considered and explicitly **not** implemented for the hackathon build — documented as a deliberate scope cut, not a silent omission.
- Logged fields: timestamp, case ID, model/risk outputs, evidence used, agent output, policy decision, human action if applicable.
- Described everywhere as **append-only**, never as "immutable" — immutability would require the hash-chaining that isn't built here.

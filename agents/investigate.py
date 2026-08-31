"""
agents/investigate.py

The single Investigation Agent (ARCHITECTURE.md Section 4). Read-only over
the evidence bundle only, structured output, no state-changing tools of any
kind, `insufficient_evidence` a first-class valid output.

Supports two LLM providers, selected via the `provider` argument or the
RAZORGUARD_LLM_PROVIDER environment variable:
  - "anthropic" (default) — needs ANTHROPIC_API_KEY, a paid API.
  - "groq" — needs GROQ_API_KEY, which has a free tier. Groq's API is
    OpenAI-compatible (chat.completions.create, a messages list with a
    "system" role entry, response.choices[0].message.content) rather than
    Anthropic's shape (a separate `system` parameter,
    response.content[i].text) — this is why provider support needed real
    code, not just swapping an environment variable.

*** VERIFICATION STATUS — READ BEFORE TRUSTING THIS FILE ***
This module's prompt construction, evidence-bundle wiring, and response
PARSING/VALIDATION (agents/schema.py) are unit-tested with a mocked/canned
model response (tests/test_investigate.py) and pass. Neither the Anthropic
nor the Groq call path has been executed in this sandbox — no key for either
provider is available here. This is not a hidden gap — it is the single
largest unverified piece of this entire build. Before treating this agent as
working, run it for real against a few actual clusters (real and
dev-scenario synthetic) with a real API key and do the evidence-grounding
review pass DAILY_BUILD_PLAN.md Day 4 Evening calls for.
"""
from __future__ import annotations

import json
import os

from agents.evidence_builder import build_evidence_bundle
from agents.schema import validate_investigation_result, SchemaValidationError, InvestigationResult

SYSTEM_PROMPT = """You are the RazorGuard Investigation Agent, reviewing a candidate coordinated \
suspicious cluster from real payments data for a human fraud analyst.

HARD RULES — violating any of these makes your output unusable:
1. You may use ONLY the evidence bundle provided below. You have no other tools, no \
database access, no web access, and no memory of other cases.
2. Every claim you make MUST be traceable to a specific field in the evidence bundle. \
Cite the exact field name for every claim.
3. This is REAL data. Call this a "coordinated suspicious cluster", never a "fraud ring". \
Shared identifiers (device, address, card) are SIGNALS, not proof — never claim "the same \
device", "the same person", or "linked accounts". Use language like "share an observed \
device-information signal".
4. If the evidence is weak or ambiguous, output "insufficient_evidence". This is a normal, \
expected, first-class outcome — not a failure. Do not escalate just to seem useful.
5. You have no ability to block, reverse, freeze, or otherwise act on any transaction or \
account. You only produce a recommendation for human review.

Respond with ONLY a JSON object, no other text, matching this exact shape:
{
  "verdict": "escalate" | "insufficient_evidence",
  "confidence": <float 0-1>,
  "claims": [
    {"claim": "<your claim, in your own words>", "cited_field": "<one of: cluster_members, \
shared_identifier_facts, temporal_pattern, transaction_risk_scores, cluster_score_breakdown>"}
  ]
}
If verdict is "insufficient_evidence", "claims" may be empty."""

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    # llama-3.3-70b-versatile is a solid free-tier Groq default for this kind
    # of structured-reasoning task; swap for another Groq-hosted model name
    # if you hit rate limits or want to compare quality.
    "groq": "llama-3.3-70b-versatile",
}


def build_user_message(evidence_bundle: dict) -> str:
    return (
        "Evidence bundle for cluster "
        f"{evidence_bundle['cluster_id']} (JSON):\n\n"
        f"{json.dumps(evidence_bundle, indent=2)}\n\n"
        "Produce your structured verdict now."
    )


def _parse_json_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise SchemaValidationError(f"agent response was not valid JSON: {e}\nraw text: {text!r}")


def _call_anthropic(evidence_bundle: dict, model: str) -> InvestigationResult:
    import anthropic  # imported here, not at module level, so this file can
    # still be imported and its non-network functions tested without the
    # anthropic package needing a configured client.

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(evidence_bundle)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return validate_investigation_result(_parse_json_response(text))


def _call_groq(evidence_bundle: dict, model: str) -> InvestigationResult:
    from groq import Groq  # imported here for the same reason as anthropic above

    client = Groq()  # reads GROQ_API_KEY from the environment
    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        response_format={"type": "json_object"},  # ask Groq to guarantee valid JSON
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(evidence_bundle)},
        ],
    )
    text = response.choices[0].message.content
    return validate_investigation_result(_parse_json_response(text))


def call_investigation_agent(
    evidence_bundle: dict, model: str | None = None, provider: str | None = None
) -> InvestigationResult:
    """
    *** NOT EXECUTED IN THIS SANDBOX — see module docstring. ***
    Requires a real API key for whichever provider is selected.

    provider: "anthropic" or "groq". Defaults to the RAZORGUARD_LLM_PROVIDER
    environment variable, or "anthropic" if that's unset — set
    RAZORGUARD_LLM_PROVIDER=groq to use Groq's free tier without touching code.
    """
    provider = provider or os.environ.get("RAZORGUARD_LLM_PROVIDER", "anthropic")
    model = model or DEFAULT_MODELS.get(provider)
    if provider == "anthropic":
        return _call_anthropic(evidence_bundle, model)
    elif provider == "groq":
        return _call_groq(evidence_bundle, model)
    else:
        raise ValueError(f"unknown provider {provider!r} — expected 'anthropic' or 'groq'")


def investigate_cluster(
    cluster_id: str,
    scored_clusters,
    qualified_edges,
    entity_representative_view,
    entity_risk_scores,
    model: str | None = None,
    provider: str | None = None,
) -> InvestigationResult:
    """Full pipeline: build the deterministic evidence bundle, then call the
    agent. This is the function backend/ actually calls
    (POST /clusters/{id}/investigate)."""
    bundle = build_evidence_bundle(
        cluster_id, scored_clusters, qualified_edges, entity_representative_view, entity_risk_scores
    )
    return call_investigation_agent(bundle, model=model, provider=provider)


"""
tests/test_investigate_providers.py

Mocked unit tests for agents/investigate.py's provider dispatch and response
parsing (Anthropic and Groq). No live API key is used or needed — both SDK
clients are mocked at the point they're constructed, so these tests exercise
the actual dispatch/parsing code paths without any network call.

These do NOT prove the real Anthropic or Groq services behave as mocked here
— see agents/investigate.py's module docstring for that honest caveat. They
prove the dispatch logic and response-shape handling are correct given a
response in each provider's real shape.
"""
from unittest.mock import MagicMock, patch

import pytest

from agents.investigate import call_investigation_agent, DEFAULT_MODELS
from agents.schema import SchemaValidationError

VALID_JSON_RESPONSE = (
    '{"verdict": "escalate", "confidence": 0.8, '
    '"claims": [{"claim": "x", "cited_field": "shared_identifier_facts"}]}'
)

_BUNDLE = {"cluster_id": "c1", "cluster_members": ["A", "B"]}


def _mock_anthropic_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _mock_groq_response(text: str):
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def test_default_provider_is_anthropic_when_unset(monkeypatch):
    monkeypatch.delenv("RAZORGUARD_LLM_PROVIDER", raising=False)
    with patch("anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = _mock_anthropic_response(VALID_JSON_RESPONSE)
        result = call_investigation_agent(_BUNDLE)
    assert result.verdict == "escalate"
    mock_client_cls.return_value.messages.create.assert_called_once()
    call_kwargs = mock_client_cls.return_value.messages.create.call_args.kwargs
    assert call_kwargs["model"] == DEFAULT_MODELS["anthropic"]
    assert "system" in call_kwargs  # Anthropic's shape: system is a separate param


def test_explicit_provider_argument_overrides_env(monkeypatch):
    monkeypatch.setenv("RAZORGUARD_LLM_PROVIDER", "anthropic")
    with patch("groq.Groq") as mock_client_cls:
        mock_client_cls.return_value.chat.completions.create.return_value = _mock_groq_response(VALID_JSON_RESPONSE)
        result = call_investigation_agent(_BUNDLE, provider="groq")
    assert result.verdict == "escalate"
    mock_client_cls.return_value.chat.completions.create.assert_called_once()


def test_groq_provider_dispatch_and_response_shape(monkeypatch):
    monkeypatch.setenv("RAZORGUARD_LLM_PROVIDER", "groq")
    with patch("groq.Groq") as mock_client_cls:
        mock_client_cls.return_value.chat.completions.create.return_value = _mock_groq_response(VALID_JSON_RESPONSE)
        result = call_investigation_agent(_BUNDLE)
    assert result.verdict == "escalate"
    assert result.confidence == 0.8
    call_kwargs = mock_client_cls.return_value.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == DEFAULT_MODELS["groq"]
    # Groq's shape: system prompt lives INSIDE the messages list, not a
    # separate `system` kwarg like Anthropic — this is the actual thing that
    # required real code, not just an env var swap.
    assert "system" not in call_kwargs
    assert call_kwargs["messages"][0]["role"] == "system"
    assert call_kwargs["response_format"] == {"type": "json_object"}


def test_invalid_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("RAZORGUARD_LLM_PROVIDER", "not_a_real_provider")
    with pytest.raises(ValueError, match="unknown provider"):
        call_investigation_agent(_BUNDLE)


def test_anthropic_malformed_json_raises_schema_validation_error(monkeypatch):
    monkeypatch.setenv("RAZORGUARD_LLM_PROVIDER", "anthropic")
    with patch("anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = _mock_anthropic_response("not valid json {{{")
        with pytest.raises(SchemaValidationError):
            call_investigation_agent(_BUNDLE)


def test_groq_malformed_json_raises_schema_validation_error(monkeypatch):
    monkeypatch.setenv("RAZORGUARD_LLM_PROVIDER", "groq")
    with patch("groq.Groq") as mock_client_cls:
        mock_client_cls.return_value.chat.completions.create.return_value = _mock_groq_response("not valid json {{{")
        with pytest.raises(SchemaValidationError):
            call_investigation_agent(_BUNDLE)


def test_groq_response_failing_schema_validation_is_rejected(monkeypatch):
    """A syntactically valid JSON response that violates the structured
    contract (e.g. an invalid verdict) must still be rejected, regardless of
    which provider produced it."""
    monkeypatch.setenv("RAZORGUARD_LLM_PROVIDER", "groq")
    bad_response = '{"verdict": "block_transaction", "confidence": 0.9, "claims": []}'
    with patch("groq.Groq") as mock_client_cls:
        mock_client_cls.return_value.chat.completions.create.return_value = _mock_groq_response(bad_response)
        with pytest.raises(SchemaValidationError):
            call_investigation_agent(_BUNDLE)


def test_model_override_argument_is_respected(monkeypatch):
    monkeypatch.setenv("RAZORGUARD_LLM_PROVIDER", "groq")
    with patch("groq.Groq") as mock_client_cls:
        mock_client_cls.return_value.chat.completions.create.return_value = _mock_groq_response(VALID_JSON_RESPONSE)
        call_investigation_agent(_BUNDLE, model="some-other-groq-model")
    call_kwargs = mock_client_cls.return_value.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "some-other-groq-model"

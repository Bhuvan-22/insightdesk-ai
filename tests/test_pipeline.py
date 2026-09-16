"""
Test suite — everything runs in mock mode, so no API key or network access
is required to verify the pipeline.
"""

from pathlib import Path

import pytest

from src.data.clean_tickets import load_and_clean, summarize
from src.data.api_client import fetch_product
from src.prompts.templates import (
    zero_shot_classify_prompt,
    few_shot_classify_prompt,
    chain_of_thought_triage_prompt,
    rtcf_reply_prompt,
)
from src.llm.client import LLMClient
from src.context.state_manager import ConversationState
from src.guardrails.policy_engine import decide, PolicyDecision

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "data" / "sample_tickets.csv"


def test_load_and_clean_drops_empty_messages_and_normalizes_fields():
    tickets = load_and_clean(SAMPLE_CSV)
    assert all(t.message for t in tickets)
    assert all(t.category in {"billing", "shipping", "refund", "general"} for t in tickets)
    assert all(t.priority in {"low", "medium", "high"} for t in tickets)


def test_summarize_returns_counts():
    tickets = load_and_clean(SAMPLE_CSV)
    stats = summarize(tickets)
    assert stats["count"] == len(tickets)
    assert "by_category" in stats


def test_prompt_templates_produce_nonempty_strings():
    msg = "My order arrived broken and I want a refund."
    assert "billing" in few_shot_classify_prompt(msg) or "refund" in few_shot_classify_prompt(msg)
    assert zero_shot_classify_prompt(msg)
    assert chain_of_thought_triage_prompt(msg)
    assert "ROLE:" in rtcf_reply_prompt(msg, "refund", "high")


def test_mock_llm_classifies_refund_message():
    client = LLMClient(mock_mode=True)
    raw = client.complete(few_shot_classify_prompt("The item arrived damaged, I want a refund."))
    assert "refund" in raw


def test_conversation_state_tracks_turns_and_respects_budget():
    state = ConversationState(llm=LLMClient(mock_mode=True), token_budget=50)
    for i in range(10):
        state.respond(f"This is message number {i} about my order status update please.")
    # Budget enforcement should have compressed older turns into a summary.
    assert state.running_summary != ""
    assert len(state.turns) < 20


def test_policy_engine_escalates_on_legal_keyword():
    class FakeTicket:
        ticket_id = "T1"
        message = "I'm going to file a chargeback if this isn't fixed."
        customer_email = "x@example.com"
        enrichment = {}

    decision = decide(FakeTicket(), category="billing", urgency="medium")
    assert isinstance(decision, PolicyDecision)
    assert decision.action == "escalate"


def test_policy_engine_requests_clarification_without_email():
    class FakeTicket:
        ticket_id = "T2"
        message = "My invoice looks wrong."
        customer_email = None
        enrichment = {}

    decision = decide(FakeTicket(), category="billing", urgency="low")
    assert decision.action == "needs_clarification"

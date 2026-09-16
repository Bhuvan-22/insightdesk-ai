"""
Conversational context engine.

Manages multi-turn state for a single customer conversation:
- Tracks turns with a persistent persona/system prompt.
- Enforces a token budget by summarizing the oldest turns once exceeded.
- Filters low-relevance turns before assembling the next prompt.

Course tie-in: Module 4 · Lessons 1-2 (Context Engineering, Context Injection
and Optimization)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.llm.client import LLMClient, get_default_client

DEFAULT_PERSONA = (
    "You are a calm, consistent, empathetic customer support agent. You stay "
    "professional even if the customer is frustrated, and you never contradict "
    "earlier commitments made in this conversation."
)

# Rough heuristic: ~4 characters per token. Good enough for budgeting demo
# purposes without pulling in a real tokenizer dependency.
CHARS_PER_TOKEN = 4


@dataclass
class Turn:
    role: str  # "customer" or "agent"
    text: str

    def token_estimate(self) -> int:
        return max(1, len(self.text) // CHARS_PER_TOKEN)


@dataclass
class ConversationState:
    persona: str = DEFAULT_PERSONA
    turns: list[Turn] = field(default_factory=list)
    running_summary: str = ""
    token_budget: int = 800
    llm: LLMClient = field(default_factory=get_default_client)

    def add_turn(self, role: str, text: str) -> None:
        self.turns.append(Turn(role=role, text=text))
        self._enforce_budget()

    def _current_token_count(self) -> int:
        summary_tokens = max(1, len(self.running_summary) // CHARS_PER_TOKEN) if self.running_summary else 0
        return summary_tokens + sum(t.token_estimate() for t in self.turns)

    def _enforce_budget(self) -> None:
        """When over budget, fold the oldest turns into the running summary
        (relevance filtering + summarization) instead of dropping them silently."""
        while self._current_token_count() > self.token_budget and len(self.turns) > 2:
            oldest = self.turns.pop(0)
            self.running_summary = self._summarize_into(self.running_summary, oldest)

    def _summarize_into(self, existing_summary: str, turn: Turn) -> str:
        prompt = (
            "Update this running conversation summary with one new turn. Keep it "
            "to 2-3 sentences, preserving any commitments made to the customer.\n\n"
            f"Existing summary: {existing_summary or '(none yet)'}\n"
            f"New turn ({turn.role}): {turn.text}"
        )
        return self.llm.complete(prompt)

    def relevant_turns(self, keep_last: int = 6) -> list[Turn]:
        """Simple relevance filter: keep the most recent N turns verbatim;
        older context lives in `running_summary` instead."""
        return self.turns[-keep_last:]

    def build_prompt(self, new_customer_message: str) -> str:
        history_block = "\n".join(f"{t.role}: {t.text}" for t in self.relevant_turns())
        summary_block = f"Conversation so far (summarized): {self.running_summary}\n\n" if self.running_summary else ""
        return (
            f"{self.persona}\n\n"
            f"{summary_block}"
            f"Recent turns:\n{history_block}\n\n"
            f"customer: {new_customer_message}\nagent:"
        )

    def respond(self, customer_message: str) -> str:
        self.add_turn("customer", customer_message)
        prompt = self.build_prompt(customer_message)
        reply = self.llm.complete(prompt)
        self.add_turn("agent", reply)
        return reply

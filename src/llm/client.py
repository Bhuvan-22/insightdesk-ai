"""
Thin LLM client wrapper.

Wraps whatever LLM provider you plug in behind one `complete()` call. If no
API key is configured, falls back to a deterministic mock so the rest of the
pipeline (and the test suite) can run fully offline.

Swap `_call_live_api` for your provider of choice (Anthropic, OpenAI, etc.) —
the rest of the codebase never needs to know which one you picked.
"""

from __future__ import annotations

import json
import os
import re

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")


class LLMClient:
    def __init__(self, api_key: str | None = None, mock_mode: bool | None = None):
        self.api_key = api_key or LLM_API_KEY
        self.mock_mode = mock_mode if mock_mode is not None else not bool(self.api_key)

    def complete(self, prompt: str, max_tokens: int = 400) -> str:
        if self.mock_mode:
            return self._mock_complete(prompt)
        return self._call_live_api(prompt, max_tokens)

    # -- live provider ---------------------------------------------------
    def _call_live_api(self, prompt: str, max_tokens: int) -> str:
        """Replace this with a real API call, e.g.:

        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        resp = client.messages.create(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
        """
        raise NotImplementedError(
            "Plug in your LLM provider here. Until then, leave LLM_API_KEY unset "
            "to run in mock mode."
        )

    # -- offline mock ------------------------------------------------------
    def _mock_complete(self, prompt: str) -> str:
        """Deterministic, rule-based stand-in for an LLM response so the whole
        pipeline is runnable and testable without network access or a key."""
        lower = prompt.lower()

        # Classification-style prompts -> return JSON
        if '"category"' in prompt and '"urgency"' in prompt:
            # Few-shot prompts repeat "Message:" once per example — the one we
            # actually need to classify is always the *last* occurrence.
            message_matches = re.findall(r'[Mm]essage:\s*"([^"]*)"', prompt)
            text = message_matches[-1].lower() if message_matches else lower

            if any(w in text for w in ["refund", "damaged", "broken", "money back"]):
                category, urgency = "refund", "high"
            elif any(w in text for w in ["charge", "invoice", "billing", "bill"]):
                category, urgency = "billing", "medium"
            elif any(w in text for w in ["package", "delivered", "shipping", "tracking", "order"]):
                category, urgency = "shipping", "high"
            else:
                category, urgency = "general", "low"

            result = {"category": category, "urgency": urgency}
            if "reasoning_summary" in prompt:
                result["reasoning_summary"] = (
                    f"Classified based on keyword signals as {category} with {urgency} urgency."
                )
            return json.dumps(result)

        # RTCF reply drafting -> return a templated but context-aware reply
        if "ROLE:" in prompt and "FORMAT:" in prompt:
            ctx_match = re.search(r'Customer message:\s*"([^"]*)"', prompt)
            complaint = ctx_match.group(1) if ctx_match else "your issue"
            snippet = complaint[:80]
            return (
                "Thank you for reaching out about this — I'm sorry for the trouble with "
                f"\"{snippet}\". I've reviewed your ticket and I'm escalating it to the "
                "right team right now. You should hear back with a concrete resolution within "
                "1 business day. In the meantime, feel free to reply here with any additional "
                "details that might help us resolve this faster."
            )

        # Invoice/document parsing mock
        if "invoice" in lower or "receipt" in lower:
            return json.dumps({
                "vendor": "Sample Vendor Inc.",
                "line_items": [
                    {"description": "Widget A", "qty": 2, "unit_price": 19.99},
                    {"description": "Widget B", "qty": 1, "unit_price": 49.99},
                ],
                "total": 89.97,
                "_source": "mock",
            })

        # Running-summary updates (ConversationState._summarize_into)
        if "running conversation summary" in lower:
            new_turn_match = re.search(r"New turn \((\w+)\):\s*(.*)", prompt, re.DOTALL)
            role, text = (new_turn_match.groups() if new_turn_match else ("customer", ""))
            return f"Customer raised: \"{text.strip()[:100]}\" — still awaiting resolution."

        # Free-form multi-turn conversation (ConversationState.build_prompt)
        if "customer:" in lower and lower.rstrip().endswith("agent:"):
            last_customer_match = re.findall(r"customer:\s*(.*)", prompt)
            last_message = last_customer_match[-1].strip() if last_customer_match else ""
            text = last_message.lower()
            if "refund" in text:
                return (
                    "I understand you'd like a refund instead of a replacement. I've flagged "
                    "your request for our billing team, and they'll follow up within 1 business "
                    "day to confirm the refund."
                )
            if any(w in text for w in ["frustrated", "angry", "unacceptable", "days now"]):
                return (
                    "I completely understand the frustration, and I'm sorry this has dragged on. "
                    "I'm prioritizing your case right now so we can get you a resolution quickly."
                )
            if any(w in text for w in ["never arrived", "not here", "missing", "delivered"]):
                return (
                    "Thanks for confirming — since tracking shows delivered but it hasn't arrived, "
                    "I'm opening a carrier investigation and will follow up with next steps shortly."
                )
            return (
                "Thanks for the extra detail — I've noted it on your ticket and will keep you "
                "updated as soon as I hear back from the relevant team."
            )

        return "[mock response] " + prompt[:120]


def get_default_client() -> LLMClient:
    return LLMClient()

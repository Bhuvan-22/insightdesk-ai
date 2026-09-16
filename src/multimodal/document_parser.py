"""
Invoice / receipt understanding.

Extracts structured line-item data from an uploaded invoice or receipt
image using a vision-capable LLM call. Falls back to a mock parse in
offline/no-key mode so the pipeline stays runnable end to end.

Course tie-in: Module 5 · Lesson 1 (Vision AI and Document Understanding)
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from src.llm.client import LLMClient, get_default_client

PARSE_PROMPT = (
    "This image is a customer invoice or receipt. Extract the vendor name, "
    "each line item (description, quantity, unit price), and the total amount. "
    "Respond as JSON: "
    '{"vendor": ..., "line_items": [{"description": ..., "qty": ..., "unit_price": ...}], "total": ...}'
)


def _encode_image(image_path: str | Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def parse_invoice(image_path: str | Path, llm: LLMClient | None = None) -> dict:
    """Parse an invoice/receipt image into structured data.

    In live mode this would send the base64 image alongside PARSE_PROMPT to a
    vision-capable model (e.g. as an `image` content block). In mock mode it
    returns a deterministic synthetic parse so the pipeline is demoable
    without an API key or a real scanned document.
    """
    llm = llm or get_default_client()
    path = Path(image_path)

    if llm.mock_mode:
        # Mock mode doesn't need the actual bytes, but we still validate the
        # file exists so the CLI gives a sensible error on a bad path.
        if not path.exists():
            raise FileNotFoundError(f"No such invoice file: {path}")
        raw = llm.complete(PARSE_PROMPT + f"\n\n[mock: pretend-analyzing {path.name}]")
        return json.loads(raw)

    # Live path (sketch): swap in your provider's multimodal message format.
    _ = _encode_image(path)  # would be attached as an image content block
    raw = llm.complete(PARSE_PROMPT)
    return json.loads(raw)


def visual_grounding_check(parsed: dict) -> list[str]:
    """Basic sanity checks so an ungrounded/hallucinated parse doesn't silently
    flow downstream — a lightweight nod to Module 5's guardrails-for-vision content."""
    warnings = []
    if not parsed.get("line_items"):
        warnings.append("No line items extracted — verify the image quality.")
    declared_total = parsed.get("total")
    computed_total = sum(
        item.get("qty", 0) * item.get("unit_price", 0) for item in parsed.get("line_items", [])
    )
    if declared_total is not None and abs(declared_total - computed_total) > 0.01:
        warnings.append(
            f"Declared total (${declared_total:.2f}) doesn't match line items "
            f"(${computed_total:.2f}) — flag for human review."
        )
    return warnings

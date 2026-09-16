"""
Prompt template library.

Implements four prompting styles covered in the course, escalating in
structure and control:

- Zero-shot classification
- Few-shot classification (in-context examples)
- Chain-of-thought triage reasoning
- RTCF (Role - Task - Context - Format) reply drafting

Course tie-in: Module 3 (Prompt Engineering & LLM Fundamentals)
"""

from __future__ import annotations

FEW_SHOT_EXAMPLES = [
    {
        "message": "I was double-charged on my card this month.",
        "category": "billing",
        "urgency": "medium",
    },
    {
        "message": "My package shows delivered but I never received it.",
        "category": "shipping",
        "urgency": "high",
    },
    {
        "message": "The blender I bought arrived cracked, I want my money back.",
        "category": "refund",
        "urgency": "high",
    },
    {
        "message": "How do I change my account email address?",
        "category": "general",
        "urgency": "low",
    },
]


def zero_shot_classify_prompt(message: str) -> str:
    return (
        "Classify the following customer support message into exactly one category: "
        "billing, shipping, refund, or general. Also assign an urgency of low, medium, "
        "or high. Respond as JSON: {\"category\": ..., \"urgency\": ...}.\n\n"
        f"Message: \"{message}\""
    )


def few_shot_classify_prompt(message: str) -> str:
    examples_block = "\n".join(
        f'Message: "{ex["message"]}"\n'
        f'-> {{"category": "{ex["category"]}", "urgency": "{ex["urgency"]}"}}'
        for ex in FEW_SHOT_EXAMPLES
    )
    return (
        "Here are examples of how to classify customer support messages:\n\n"
        f"{examples_block}\n\n"
        "Now classify this new message in the same JSON format:\n"
        f'Message: "{message}"\n->'
    )


def chain_of_thought_triage_prompt(message: str, enrichment: dict | None = None) -> str:
    context_line = ""
    if enrichment and enrichment.get("product"):
        product = enrichment["product"]
        context_line = f"\nRelevant product context: {product.get('title', 'unknown item')}."

    return (
        "You are triaging a support ticket. Think step by step before deciding:\n"
        "1. Identify what the customer is asking for.\n"
        "2. Identify any urgency signals (money, time-sensitivity, repeated contact).\n"
        "3. Decide the category and urgency.\n"
        "4. State your final answer as JSON on the last line: "
        '{"category": ..., "urgency": ..., "reasoning_summary": "..."}.\n'
        f"{context_line}\n\n"
        f'Message: "{message}"'
    )


def rtcf_reply_prompt(
    message: str,
    category: str,
    urgency: str,
    customer_name: str | None = None,
    policy_notes: str | None = None,
) -> str:
    """RTCF = Role, Task, Context, Format — a structured framework for drafting
    a customer-facing reply with a consistent tone and explicit constraints."""
    role = (
        "You are a calm, empathetic customer support agent for an e-commerce company. "
        "You are professional, concise, and never make promises the company can't keep."
    )
    task = (
        f"Draft a reply to a {urgency}-urgency {category} ticket. Acknowledge the issue, "
        "explain the next concrete step, and set a realistic expectation for follow-up."
    )
    context = (
        f'Customer message: "{message}"\n'
        f"Customer name: {customer_name or 'the customer'}\n"
        f"Policy notes to respect: {policy_notes or 'standard policy applies'}"
    )
    format_ = (
        "Write 3-5 sentences. No subject line. No sign-off placeholder text like "
        "'[Your Name]'. Plain prose, no bullet points."
    )
    return f"ROLE:\n{role}\n\nTASK:\n{task}\n\nCONTEXT:\n{context}\n\nFORMAT:\n{format_}"

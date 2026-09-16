"""
Policy-bound guardrails.

Hard business rules that sit *outside* the LLM's judgment: refund caps,
auto-escalation triggers, clarification requirements, and a fixed rule for
resolving conflicts between user claims and system policy. Every decision
is emitted as a structured record so it can be logged, audited, or handed
to a human agent.

Course tie-in: Module 4 · Lesson 3 (Guardrails, Policy-Bound Decisions,
Structured Outputs)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

REFUND_AUTO_APPROVE_LIMIT = 50.00
ESCALATION_KEYWORDS = {"lawyer", "legal action", "chargeback", "fraud", "scam"}


@dataclass
class PolicyDecision:
    ticket_id: str
    action: str  # "auto_resolve" | "escalate" | "needs_clarification"
    reason: str
    max_refund_amount: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _order_value(enrichment: dict | None) -> float | None:
    if not enrichment:
        return None
    product = enrichment.get("product")
    if not product:
        return None
    return product.get("price")


def decide(ticket, category: str, urgency: str) -> PolicyDecision:
    """Apply policy rules to a classified ticket. System policy always wins
    over anything the customer asserts in free text (conflict-resolution rule)."""
    message_lower = ticket.message.lower()

    # Rule 1: explicit legal/fraud escalation triggers always escalate, no exceptions.
    if any(kw in message_lower for kw in ESCALATION_KEYWORDS):
        return PolicyDecision(
            ticket_id=ticket.ticket_id,
            action="escalate",
            reason="Escalation keyword detected — routing to a human agent regardless of category.",
        )

    # Rule 2: refund requests need a resolvable order value to auto-approve.
    if category == "refund":
        order_value = _order_value(ticket.enrichment)
        if order_value is None:
            return PolicyDecision(
                ticket_id=ticket.ticket_id,
                action="needs_clarification",
                reason="Refund requested but no product/order value could be resolved. "
                       "Ask the customer for an order number before proceeding.",
            )
        if order_value <= REFUND_AUTO_APPROVE_LIMIT:
            return PolicyDecision(
                ticket_id=ticket.ticket_id,
                action="auto_resolve",
                reason=f"Refund of ${order_value:.2f} is within the auto-approve limit "
                       f"(${REFUND_AUTO_APPROVE_LIMIT:.2f}).",
                max_refund_amount=order_value,
            )
        return PolicyDecision(
            ticket_id=ticket.ticket_id,
            action="escalate",
            reason=f"Refund of ${order_value:.2f} exceeds the auto-approve limit — "
                   "requires manager sign-off.",
        )

    # Rule 3: missing contact info on a billing/shipping issue needs clarification.
    if category in {"billing", "shipping"} and not ticket.customer_email:
        return PolicyDecision(
            ticket_id=ticket.ticket_id,
            action="needs_clarification",
            reason="No customer email on file — cannot follow up without contact info.",
        )

    # Rule 4: high urgency shipping/billing issues get escalated for a human review.
    if urgency == "high" and category in {"billing", "shipping"}:
        return PolicyDecision(
            ticket_id=ticket.ticket_id,
            action="escalate",
            reason="High-urgency billing/shipping issue — routed to a human agent as a precaution.",
        )

    return PolicyDecision(
        ticket_id=ticket.ticket_id,
        action="auto_resolve",
        reason="No policy blockers found; safe for the AI-drafted reply to go out as-is.",
    )

"""
Ticket cleaning pipeline.

Takes a raw, messy support-ticket CSV (missing fields, inconsistent casing,
stray whitespace, duplicate follow-ups) and turns it into a list of clean,
typed `Ticket` records ready for enrichment and prompting.

Course tie-in: Module 2 · Lesson 1 (Tabular Data Cleaning with Pandas)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

VALID_CATEGORIES = {"billing", "shipping", "refund", "general"}
VALID_PRIORITIES = {"low", "medium", "high"}
DEFAULT_PRIORITY = "medium"
DEFAULT_CATEGORY = "general"


@dataclass
class Ticket:
    ticket_id: str
    customer_email: Optional[str]
    product_id: Optional[str]
    category: str
    message: str
    priority: str
    enrichment: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "customer_email": self.customer_email,
            "product_id": self.product_id,
            "category": self.category,
            "message": self.message,
            "priority": self.priority,
            "enrichment": self.enrichment,
        }


def _normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_category(value) -> str:
    text = _normalize_text(value).lower()
    return text if text in VALID_CATEGORIES else DEFAULT_CATEGORY


def _normalize_priority(value) -> str:
    text = _normalize_text(value).lower()
    return text if text in VALID_PRIORITIES else DEFAULT_PRIORITY


def load_and_clean(csv_path: str | Path) -> list[Ticket]:
    """Load a raw ticket CSV and return a list of cleaned Ticket objects.

    Cleaning rules:
    - Drop rows with no message body (nothing actionable to process).
    - Trim whitespace on all string fields.
    - Normalize category/priority to a fixed vocabulary, defaulting when
      the value is missing or unrecognized.
    - Treat blank emails / product ids as `None` rather than empty strings.
    - Drop exact duplicate ticket_ids, keeping the first occurrence.
    """
    df = pd.read_csv(csv_path, dtype=str)

    df["message"] = df["message"].map(_normalize_text)
    df = df[df["message"] != ""].copy()

    df["customer_email"] = df["customer_email"].map(_normalize_text)
    df["product_id"] = df["product_id"].map(_normalize_text)
    df["category"] = df["category"].map(_normalize_category)
    df["priority"] = df["priority"].map(_normalize_priority)

    df = df.drop_duplicates(subset="ticket_id", keep="first")

    # Build Ticket objects directly rather than round-tripping empty-string ->
    # None through a pandas column, since object columns can silently coerce
    # None back to NaN (and float NaN is truthy in plain Python, which would
    # break downstream `if not ticket.customer_email` checks).
    tickets = [
        Ticket(
            ticket_id=row["ticket_id"],
            customer_email=row["customer_email"] or None,
            product_id=row["product_id"] or None,
            category=row["category"],
            message=row["message"],
            priority=row["priority"],
        )
        for _, row in df.iterrows()
    ]
    return tickets


def summarize(tickets: list[Ticket]) -> dict:
    """Quick aggregate stats, handy for a CLI summary or a dashboard."""
    if not tickets:
        return {"count": 0}
    df = pd.DataFrame([t.to_dict() for t in tickets])
    return {
        "count": len(tickets),
        "by_category": df["category"].value_counts().to_dict(),
        "by_priority": df["priority"].value_counts().to_dict(),
        "missing_email": int(df["customer_email"].isna().sum()),
    }


if __name__ == "__main__":
    tickets = load_and_clean(Path(__file__).resolve().parents[2] / "data" / "sample_tickets.csv")
    for t in tickets:
        print(t.to_dict())
    print("\nSummary:", summarize(tickets))

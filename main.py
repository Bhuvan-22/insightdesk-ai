"""
InsightDesk AI — CLI orchestrator.

Chains together every module built across the 6-day plan:
data cleaning -> API enrichment -> classification -> context-aware reply
drafting -> policy guardrails -> (optional) multimodal / voice input.

Usage:
    python main.py --demo
    python main.py --tickets data/sample_tickets.csv
    python main.py --invoice path/to/invoice.png
    python main.py --voice path/to/complaint.wav --speak-reply
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.clean_tickets import load_and_clean, summarize, Ticket
from src.data.api_client import enrich_ticket
from src.prompts.templates import few_shot_classify_prompt, rtcf_reply_prompt
from src.llm.client import get_default_client
from src.guardrails.policy_engine import decide
from src.context.state_manager import ConversationState
from src.multimodal.document_parser import parse_invoice, visual_grounding_check
from src.voice.speech_pipeline import transcribe, synthesize_speech

ROOT = Path(__file__).resolve().parent


def process_ticket(ticket: Ticket, llm) -> dict:
    enrich_ticket(ticket)

    classification_raw = llm.complete(few_shot_classify_prompt(ticket.message))
    try:
        classification = json.loads(classification_raw)
    except json.JSONDecodeError:
        classification = {"category": ticket.category, "urgency": ticket.priority}

    category = classification.get("category", ticket.category)
    urgency = classification.get("urgency", ticket.priority)

    reply = llm.complete(
        rtcf_reply_prompt(
            message=ticket.message,
            category=category,
            urgency=urgency,
            customer_name=ticket.customer_email,
        )
    )

    decision = decide(ticket, category, urgency)

    return {
        "ticket": ticket.to_dict(),
        "classification": {"category": category, "urgency": urgency},
        "drafted_reply": reply,
        "policy_decision": decision.to_dict(),
    }


def run_ticket_pipeline(csv_path: Path) -> list[dict]:
    llm = get_default_client()
    tickets = load_and_clean(csv_path)
    print(f"Loaded {len(tickets)} cleaned tickets. Summary: {summarize(tickets)}\n")

    results = [process_ticket(t, llm) for t in tickets]
    for r in results:
        print(f"--- Ticket {r['ticket']['ticket_id']} ---")
        print(f"Category/Urgency: {r['classification']}")
        print(f"Policy decision:  {r['policy_decision']['action']} — {r['policy_decision']['reason']}")
        print(f"Drafted reply:    {r['drafted_reply']}\n")
    return results


def run_invoice_pipeline(image_path: Path) -> dict:
    llm = get_default_client()
    parsed = parse_invoice(image_path, llm=llm)
    warnings = visual_grounding_check(parsed)
    print("Parsed invoice:", json.dumps(parsed, indent=2))
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f" - {w}")
    return parsed


def run_voice_pipeline(audio_path: Path, speak_reply: bool) -> None:
    llm = get_default_client()
    transcript = transcribe(audio_path, llm=llm)
    print(f"Transcript: {transcript}\n")

    state = ConversationState(llm=llm)
    reply = state.respond(transcript)
    print(f"Agent reply: {reply}")

    if speak_reply:
        out_path = ROOT / "data" / "reply_audio"
        written = synthesize_speech(reply, out_path, llm=llm)
        print(f"\n(Voice reply written to: {written})")


def run_demo() -> None:
    print("=" * 60)
    print("STEP 1-2: Ticket pipeline (cleaning + enrichment + classification)")
    print("=" * 60)
    run_ticket_pipeline(ROOT / "data" / "sample_tickets.csv")

    print("=" * 60)
    print("STEP 3: Multi-turn context engine demo")
    print("=" * 60)
    llm = get_default_client()
    state = ConversationState(llm=llm)
    for msg in [
        "My package never arrived even though it says delivered.",
        "It's been 5 days now, I'm getting really frustrated.",
        "Can you just refund me instead of resending it?",
    ]:
        print(f"customer: {msg}")
        print(f"agent: {state.respond(msg)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="InsightDesk AI pipeline")
    parser.add_argument("--demo", action="store_true", help="Run the full demo pipeline")
    parser.add_argument("--tickets", type=str, help="Path to a ticket CSV to process")
    parser.add_argument("--invoice", type=str, help="Path to an invoice/receipt image to parse")
    parser.add_argument("--voice", type=str, help="Path to a voice complaint audio file")
    parser.add_argument("--speak-reply", action="store_true", help="Synthesize a spoken reply for --voice")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.tickets:
        run_ticket_pipeline(Path(args.tickets))
    elif args.invoice:
        run_invoice_pipeline(Path(args.invoice))
    elif args.voice:
        run_voice_pipeline(Path(args.voice), speak_reply=args.speak_reply)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

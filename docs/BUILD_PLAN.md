# 6-Day Build Plan

Each day is scoped to ~2-4 hours and produces a working, committable increment.
Commit at the end of every day — your git history becomes a visible progress log,
which is exactly what makes this a strong GitHub portfolio piece.

---

## Day 1 — Foundations & Data Pipeline
**Course tie-in:** Module 1 (Python Fundamentals, Git, APIs) + Module 2 · Lesson 1 (Pandas)

- Initialize the repo, virtual env, `.gitignore`, `requirements.txt`.
- Write `src/data/clean_tickets.py`: load `data/sample_tickets.csv`, handle missing /
  malformed fields, normalize categories, dedupe.
- Write a small `Ticket` dataclass to represent a cleaned record.
- Commit: `feat: project scaffold + ticket cleaning pipeline`

**Deliverable:** `python -m src.data.clean_tickets` prints a cleaned, structured
ticket list from the raw CSV.

---

## Day 2 — Resilient API Integration
**Course tie-in:** Module 2 · Lesson 2 (Public APIs, fallback caching)

- Write `src/data/api_client.py`: fetch product/customer enrichment data from a public
  API (e.g. a product-catalog or fake-store style API).
- Add retry logic + a local JSON fallback cache so a failed request degrades
  gracefully instead of crashing the pipeline.
- Wire enrichment into the Day 1 ticket objects.
- Commit: `feat: resilient API client with fallback caching`

**Deliverable:** Tickets now carry enriched product/customer context, even if you
disconnect from the network mid-run (cache kicks in).

---

## Day 3 — Prompt Engineering Engine
**Course tie-in:** Module 3 (Prompting techniques, RTCF framework)

- Write `src/prompts/templates.py` with four template families:
  zero-shot classification, few-shot classification (in-context examples),
  chain-of-thought triage reasoning, and a full RTCF (Role–Task–Context–Format)
  reply-drafting template.
- Write `src/llm/client.py`: a thin wrapper around an LLM call, with a
  deterministic **mock mode** for offline testing.
- Build a `classify_and_draft(ticket)` function that ties templates + client together.
- Commit: `feat: prompt engineering engine (zero/few-shot, CoT, RTCF)`

**Deliverable:** Given a cleaned ticket, the system outputs a category, urgency
score, and a drafted reply.

---

## Day 4 — Context Engineering & Conversational State
**Course tie-in:** Module 4 · Lessons 1-2 (context engineering, injection, summarization)

- Write `src/context/state_manager.py`: a `ConversationState` class that tracks
  turns, enforces a token budget, summarizes old turns once the budget is exceeded,
  and filters irrelevant history before each LLM call.
- Add persona conditioning (a consistent "support agent" system prompt) so tone
  stays stable across turns.
- Commit: `feat: multi-turn context engine with token budgeting + summarization`

**Deliverable:** A simulated multi-turn conversation stays coherent and under a
configurable token budget, with old turns compressed into a running summary.

---

## Day 5 — Guardrails & Multimodal Document Understanding
**Course tie-in:** Module 4 · Lesson 3 (guardrails, structured output) +
Module 5 · Lesson 1 (vision / document understanding)

- Write `src/guardrails/policy_engine.py`: hard rules (e.g. refund caps,
  auto-escalation triggers), a clarification path for incomplete context, and a
  conflict-resolution rule (system policy always wins over a user's in-chat claim).
- Enforce a structured JSON output schema for every finalized ticket decision.
- Write `src/multimodal/document_parser.py`: extract line items/totals from an
  uploaded invoice or receipt image using a vision-capable LLM call (mock-mode
  fallback returns a synthetic parse for offline demos).
- Commit: `feat: policy guardrails + invoice/receipt understanding`

**Deliverable:** The assistant refuses/escalates out-of-policy requests instead of
improvising, and can turn a receipt photo into structured line-item data.

---

## Day 6 — Voice AI & Final Assembly
**Course tie-in:** Module 5 · Lessons 2-3 (STT/TTS, multimodal assistant architecture)

- Write `src/voice/speech_pipeline.py`: speech-to-text for incoming voice
  complaints, text-to-speech for spoken replies (mock-mode fallback for offline use).
- Write `main.py`: a CLI orchestrator (`--demo`, `--tickets`, `--invoice`, `--voice`)
  that chains every module built over the past 5 days into one pipeline.
- Write `tests/test_pipeline.py` covering each module in mock mode.
- Polish `README.md`, add a LICENSE, and record a short demo (GIF or asciinema)
  for the top of the README.
- Commit: `feat: voice pipeline + end-to-end CLI orchestrator` → tag `v1.0`

**Deliverable:** `python main.py --demo` runs the entire pipeline — clean data,
enrich, classify, converse, guard, and (optionally) speak — end to end.

---

## Why this is a strong portfolio project

- It's not a single-concept toy — it demonstrates the *full stack* of a modern LLM
  application: data engineering, prompting, state management, safety guardrails,
  and multimodal I/O.
- The 6 daily commits give evaluators a readable history of how you build, not just
  a finished blob.
- Every module works offline in mock mode, so anyone cloning the repo can run and
  verify it in under a minute — no API key required to see it work.

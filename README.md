# InsightDesk AI

**An AI-powered customer support & document-insights assistant** — built as a capstone
that ties together Python engineering, data pipelines, prompt engineering, context
management, guardrails, and multimodal/voice AI into a single working system.

> Built as a 6-day sprint project. See [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) for the
> full day-by-day breakdown and which skills each day exercises.

---

## What it does

InsightDesk AI is a support-desk copilot that a small team could actually use:

1. **Ingests messy support tickets** (CSV) and cleans them with Pandas.
2. **Enriches tickets** with live product/customer data from a public API, with a
   resilient fallback-cache so the pipeline never hard-fails on a network blip.
3. **Classifies & drafts replies** to tickets using a prompt-engineering stack
   (zero-shot → few-shot → chain-of-thought → the RTCF framework).
4. **Holds a multi-turn conversation** with a customer via a context engine that does
   token budgeting, relevance filtering, and long-term summarization.
5. **Applies guardrails** — refund limits, escalation rules, and clarification prompts —
   so the assistant only takes actions the business actually allows, and always emits a
   structured ticket record.
6. **Reads uploaded invoices/receipts** (images) and extracts line items via a
   vision-capable LLM call.
7. **Accepts voice complaints** (speech-to-text) and can reply out loud (text-to-speech).

Everything runs through one CLI orchestrator (`main.py`) so you can demo the whole
pipeline end-to-end, or import any module independently.

## Architecture

```
                       ┌────────────────────┐
   tickets.csv ───────▶│  data/clean_tickets │──┐
                       └────────────────────┘  │
                                                ▼
   public API ───────▶ data/api_client.py ──▶  ticket record (enriched)
   (+ local cache)                              │
                                                 ▼
                                    ┌─────────────────────────┐
   invoice.png ──────▶ multimodal ─▶│                         │
   voice.wav   ──────▶ voice ──────▶│   context/state_manager │◀── prompts/templates
                                    │   (conversation memory)  │    (few-shot, CoT, RTCF)
                                    └───────────┬─────────────┘
                                                 ▼
                                      guardrails/policy_engine
                                                 │
                                                 ▼
                                       structured ticket output
                                       (+ optional TTS reply)
```

## Project layout

```
insightdesk-ai/
├── main.py                        # CLI orchestrator — runs the full pipeline
├── requirements.txt
├── .env.example
├── data/
│   └── sample_tickets.csv         # toy dataset to demo the pipeline
├── src/
│   ├── data/
│   │   ├── clean_tickets.py       # Pandas cleaning (Module 2 · Lesson 1)
│   │   └── api_client.py          # resilient API caller + fallback cache (Module 2 · Lesson 2)
│   ├── prompts/
│   │   └── templates.py           # zero/few-shot, CoT, RTCF templates (Module 3)
│   ├── llm/
│   │   └── client.py              # thin LLM wrapper, works in mock mode w/o a key
│   ├── context/
│   │   └── state_manager.py       # multi-turn state, token budget, summarization (Module 4 · L1-2)
│   ├── guardrails/
│   │   └── policy_engine.py       # policy-bound decisions, clarification, structured output (Module 4 · L3)
│   ├── multimodal/
│   │   └── document_parser.py     # invoice/receipt understanding (Module 5 · L1)
│   └── voice/
│       └── speech_pipeline.py     # STT + TTS wrapper (Module 5 · L2-3)
├── tests/
│   └── test_pipeline.py
└── docs/
    └── BUILD_PLAN.md              # the 6-day plan, mapped to your course modules
```

## Setup

```bash
git clone https://github.com/<your-username>/insightdesk-ai.git
cd insightdesk-ai
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # add an API key if you want live LLM calls
```

**No API key? No problem.** Every module has a `mock_mode` fallback so the whole
pipeline runs deterministically offline — useful for demos, CI, and grading.

## Run it

```bash
# Full pipeline demo on the sample dataset
python main.py --demo

# Process your own tickets
python main.py --tickets data/sample_tickets.csv

# Feed it a scanned invoice
python main.py --invoice path/to/invoice.png

# Feed it a voice complaint (wav/mp3)
python main.py --voice path/to/complaint.wav --speak-reply
```

## Testing

```bash
pytest tests/ -v
```

## Roadmap ideas (good "day 7+" stretch goals)

- Swap the CSV ingest for a real ticketing-system webhook (Zendesk/Intercom).
- Add a lightweight FastAPI layer so the assistant can run as a service.
- Persist conversation state in SQLite instead of in-memory.
- Add a Streamlit dashboard for support agents to review AI-drafted replies.

## License

MIT — see [`LICENSE`](LICENSE).

from pathlib import Path
import json
import streamlit as st

from src.data.clean_tickets import load_and_clean, summarize, Ticket
from src.data.api_client import enrich_ticket
from src.prompts.templates import few_shot_classify_prompt, rtcf_reply_prompt
from src.llm.client import get_default_client
from src.guardrails.policy_engine import decide
from src.context.state_manager import ConversationState
from src.multimodal.document_parser import parse_invoice, visual_grounding_check
from src.voice.speech_pipeline import transcribe

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="InsightDesk AI", page_icon="🤖", layout="wide")

st.markdown("# 🤖 InsightDesk AI")
st.caption("AI-powered customer support: tickets • context • guardrails • invoices • voice")

llm = get_default_client()


def process_single_ticket(message, email="", product_id="", category="general", priority="medium"):
    ticket = Ticket(
        ticket_id="WEB-001",
        customer_email=email.strip() or None,
        product_id=product_id.strip() or None,
        category=category,
        message=message.strip(),
        priority=priority,
    )
    enrich_ticket(ticket)
    raw = llm.complete(few_shot_classify_prompt(ticket.message))
    try:
        classification = json.loads(raw)
    except json.JSONDecodeError:
        classification = {"category": ticket.category, "urgency": ticket.priority}

    category = classification.get("category", ticket.category)
    urgency = classification.get("urgency", ticket.priority)
    reply = llm.complete(rtcf_reply_prompt(
        message=ticket.message,
        category=category,
        urgency=urgency,
        customer_name=ticket.customer_email,
    ))
    decision = decide(ticket, category, urgency)
    return ticket, category, urgency, reply, decision


# Session state for the multi-turn context demo
if "conversation" not in st.session_state:
    st.session_state.conversation = ConversationState(llm=llm)

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Choose a module", [
        "🎫 Ticket Assistant",
        "💬 Context Chat",
        "🧾 Invoice Parser",
        "🎤 Voice Complaint",
        "📊 Ticket CSV Dashboard",
    ])
    st.divider()
    st.info("This version uses your existing project modules. Without LLM_API_KEY, the project runs in its built-in mock/demo mode.")

if page == "🎫 Ticket Assistant":
    st.subheader("Process a customer complaint")
    with st.form("ticket_form"):
        message = st.text_area("Customer message", placeholder="My package never arrived even though it says delivered.", height=130)
        c1, c2 = st.columns(2)
        email = c1.text_input("Customer email (optional)")
        product_id = c2.text_input("Product ID (optional)")
        submitted = st.form_submit_button("🚀 Analyze Ticket", type="primary")

    if submitted:
        if not message.strip():
            st.warning("Please enter a customer message.")
        else:
            with st.spinner("Processing ticket..."):
                ticket, category, urgency, reply, decision = process_single_ticket(message, email, product_id)
            a, b, c = st.columns(3)
            a.metric("Category", category)
            b.metric("Urgency", urgency)
            c.metric("Policy Action", decision.action)
            st.markdown("### 🤖 Drafted Reply")
            st.success(reply)
            st.markdown("### 🛡️ Policy / Guardrail Result")
            st.write(decision.reason)
            if decision.max_refund_amount is not None:
                st.write(f"Maximum auto-approved refund: ${decision.max_refund_amount:.2f}")
            with st.expander("Ticket details"):
                st.json(ticket.to_dict())

elif page == "💬 Context Chat":
    st.subheader("Multi-turn Context Engine")
    st.write("Send multiple messages. The assistant keeps recent conversation context and can summarize older turns when the token budget is exceeded.")
    for turn in st.session_state.conversation.turns:
        with st.chat_message("user" if turn.role == "customer" else "assistant"):
            st.write(turn.text)

    msg = st.chat_input("Type a customer message...")
    if msg:
        reply = st.session_state.conversation.respond(msg)
        st.rerun()
    if st.button("Clear conversation"):
        st.session_state.conversation = ConversationState(llm=llm)
        st.rerun()

elif page == "🧾 Invoice Parser":
    st.subheader("Invoice / Receipt Understanding")
    uploaded = st.file_uploader("Upload an invoice or receipt image", type=["png", "jpg", "jpeg"])
    if uploaded:
        st.image(uploaded, caption="Uploaded document", width=500)
        if st.button("🔍 Parse Invoice", type="primary"):
            temp = ROOT / "data" / "web_upload_invoice" + Path(uploaded.name).suffix if False else ROOT / "data" / ("web_" + uploaded.name)
            temp.parent.mkdir(parents=True, exist_ok=True)
            temp.write_bytes(uploaded.getbuffer())
            try:
                parsed = parse_invoice(temp, llm=llm)
                warnings = visual_grounding_check(parsed)
                st.json(parsed)
                if warnings:
                    st.warning("\n".join(warnings))
                else:
                    st.success("Invoice passed the basic visual consistency checks.")
            finally:
                temp.unlink(missing_ok=True)

elif page == "🎤 Voice Complaint":
    st.subheader("Voice Complaint")
    audio = st.file_uploader("Upload a voice complaint", type=["wav", "mp3", "m4a", "ogg"])
    if audio:
        st.audio(audio)
        if st.button("🎤 Transcribe Complaint", type="primary"):
            temp = ROOT / "data" / ("web_" + audio.name)
            temp.parent.mkdir(parents=True, exist_ok=True)
            temp.write_bytes(audio.getbuffer())
            try:
                transcript = transcribe(temp, llm=llm)
                st.markdown("### Transcript")
                st.write(transcript)
                st.info("In the current project, live ASR/TTS is still a provider integration point. With no API key, the built-in mock transcript is used.")
            finally:
                temp.unlink(missing_ok=True)

elif page == "📊 Ticket CSV Dashboard":
    st.subheader("Ticket CSV Dashboard")
    uploaded = st.file_uploader("Upload a ticket CSV", type=["csv"])
    if uploaded:
        temp = ROOT / "data" / ("web_" + uploaded.name)
        temp.parent.mkdir(parents=True, exist_ok=True)
        temp.write_bytes(uploaded.getbuffer())
        try:
            tickets = load_and_clean(temp)
            summary = summarize(tickets)
            c1, c2, c3 = st.columns(3)
            c1.metric("Clean tickets", summary["count"])
            c2.metric("Missing email", summary["missing_email"])
            c3.metric("Categories", len(summary.get("by_category", {})))
            st.markdown("### Category summary")
            st.json(summary.get("by_category", {}))
            st.markdown("### Priority summary")
            st.json(summary.get("by_priority", {}))
            if st.button("🚀 Process all tickets"):
                rows = []
                progress = st.progress(0)
                for i, ticket in enumerate(tickets):
                    _, category, urgency, reply, decision = process_single_ticket(
                        ticket.message, ticket.customer_email or "", ticket.product_id or "", ticket.category, ticket.priority
                    )
                    rows.append({"ticket_id": ticket.ticket_id, "category": category, "urgency": urgency, "policy_action": decision.action, "drafted_reply": reply})
                    progress.progress((i + 1) / max(1, len(tickets)))
                st.dataframe(rows, use_container_width=True)
        finally:
            temp.unlink(missing_ok=True)

st.divider()
st.caption("InsightDesk AI — web interface added around the original CLI pipeline.")

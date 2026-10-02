"""The chat screen. Run with: streamlit run app.py

Streamlit re-runs this whole file from top to bottom every time the user
does anything. Whatever must survive between runs (the conversation, the
database) is kept in st.session_state, which is private to each browser tab.
"""

import os

import anthropic
import streamlit as st

import config
from core.conversation import Conversation
from data.seed import CUSTOMERS

st.set_page_config(page_title=f"{config.BANK_NAME} · Asistente", page_icon="💬")


def read_secret(name: str):
    """Look in environment variables first, then in Streamlit's secrets."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        return st.secrets.get(name)
    except Exception:
        if os.path.exists(".streamlit/secrets.toml"):
            # Deliberately not showing the error text: it can contain the key.
            st.error("Could not read .streamlit/secrets.toml. "
                     "Check that every value is inside double quotes.")
            st.stop()
        return None  # no secrets file at all


# --- Passcode gate (only active when APP_PASSCODE is set) ---
passcode = read_secret("APP_PASSCODE")
if passcode and not st.session_state.get("unlocked"):
    entered = st.text_input("Passcode", type="password")
    if entered == passcode:
        st.session_state.unlocked = True
        st.rerun()
    elif entered:
        st.error("Wrong passcode.")
    st.stop()

api_key = read_secret("ANTHROPIC_API_KEY")
if not api_key:
    st.error("ANTHROPIC_API_KEY is not set. See README.md, step 2.")
    st.stop()
os.environ["ANTHROPIC_API_KEY"] = api_key


# --- Per-session state ---
UNKNOWN_PHONE = "+52 00 0000 0000"
PHONES = {f"{c['full_name']} · {c['phone']}": c["phone"] for c in CUSTOMERS}
PHONES["Unknown number"] = UNKNOWN_PHONE


def start_conversation(phone: str):
    st.session_state.conversation = Conversation(phone)  # own database copy
    st.session_state.transcript = []  # (role, text, tool events) to display
    st.session_state.turns = 0


with st.sidebar:
    st.header("Demo controls")
    label = st.selectbox("Chat is coming from", list(PHONES))
    phone = PHONES[label]
    current = st.session_state.get("conversation")
    if current is None or current.session.phone != phone:
        start_conversation(phone)
    if st.button("Reset conversation and data"):
        start_conversation(phone)

    conversation = st.session_state.conversation
    session = conversation.session
    st.subheader("Session state")
    st.write("Identity:", "✅ verified" if session.verified else "🔒 not verified")
    st.write("Failed attempts:", f"{session.failed_attempts} of {config.MAX_VERIFICATION_ATTEMPTS}")
    st.write("Handed off:", "yes" if session.handed_off else "no")
    st.download_button("Download conversation log", conversation.log.as_text(),
                       file_name=f"{conversation.log.session_id}.jsonl")
    st.caption(f"Model: {config.MODEL} · effort: {config.EFFORT}")
    st.caption("All customers and figures are fictional.")


def show_tool_events(events):
    """The 'what the agent did' panel under a reply."""
    calls = [e for e in events if e["type"] in ("tool_call", "tool_result")]
    if not calls:
        return
    with st.expander(f"What the agent did ({len(calls) // 2} tool calls)"):
        for e in calls:
            if e["type"] == "tool_call":
                st.markdown(f"**{e['tool']}** `{e['input']}`")
            elif e["is_error"]:
                st.error(f"Refused: {e['result']}")
            else:
                st.success(e["result"])


st.title(f"{config.BANK_NAME} · Asistente virtual")

for role, text, events in st.session_state.transcript:
    with st.chat_message(role):
        st.write(text)
        show_tool_events(events)

user_text = st.chat_input("Escriba su mensaje")
if user_text:
    if st.session_state.turns >= config.MAX_TURNS_PER_SESSION:
        st.warning("Session limit reached. Use the reset button to start again.")
        st.stop()
    st.session_state.turns += 1
    st.session_state.transcript.append(("user", user_text, []))
    st.chat_message("user").write(user_text)

    events_before = len(conversation.log.events)
    try:
        with st.spinner("Escribiendo..."):
            reply = conversation.send(user_text)
    except anthropic.AuthenticationError:
        st.error("The API key was rejected. Check ANTHROPIC_API_KEY.")
        st.stop()
    except anthropic.RateLimitError:
        st.error("Rate limit reached. Wait a minute and try again.")
        st.stop()
    except anthropic.APIStatusError as e:
        st.error(f"The model API returned an error ({e.status_code}): {e.message}")
        st.stop()
    except anthropic.APIConnectionError:
        st.error("Could not reach the model API. Check the internet connection.")
        st.stop()

    new_events = conversation.log.events[events_before:]
    st.session_state.transcript.append(("assistant", reply, new_events))
    st.rerun()  # redraw so the sidebar shows the updated session state

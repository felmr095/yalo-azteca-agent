"""The chat screen. Run with: streamlit run app.py

Streamlit re-runs this whole file from top to bottom every time the user
does anything. Whatever must survive between runs (the conversation, the
database) is kept in st.session_state, which is private to each browser tab.
"""

import os

import anthropic
import streamlit as st

import config
from core.conversation import Conversation, OutboundNotAllowed
from core.modules import load_modules
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
UNKNOWN_PHONE, UNKNOWN_LABEL = "+52 00 0000 0000", "Unknown number"
PHONES = {f"{c['full_name']} · {c['phone']}": c["phone"] for c in CUSTOMERS}
PHONES[UNKNOWN_LABEL] = UNKNOWN_PHONE
FIRST_NAMES = {c["phone"]: c["first_name"] for c in CUSTOMERS}

# Who writes first: the customer, or the bank on behalf of a use case.
CUSTOMER_FIRST = "Customer writes first"
STARTS = {CUSTOMER_FIRST: None}
for module in load_modules():
    if module.outbound_reason:
        STARTS[f"Bank reaches out: {module.name}"] = module.name

# The start each customer's story calls for (set in data/seed.py). Picking a
# customer selects it; the dropdown can still be changed.
DEFAULT_START = {UNKNOWN_LABEL: CUSTOMER_FIRST}
for c in CUSTOMERS:
    start = f"Bank reaches out: {c.get('demo_start')}"
    DEFAULT_START[f"{c['full_name']} · {c['phone']}"] = start if start in STARTS else CUSTOMER_FIRST


def shown(text: str) -> str:
    """Streamlit reads $...$ as a formula, so amounts would turn into one.
    Escape the dollar signs so they appear as written."""
    return text.replace("$", "\\$")


def api_problem(error: anthropic.APIError) -> str:
    """A model API failure in words, without leaking the key."""
    if isinstance(error, anthropic.AuthenticationError):
        return "The API key was rejected. Check ANTHROPIC_API_KEY."
    if isinstance(error, anthropic.RateLimitError):
        return "Rate limit reached. Wait a minute and try again."
    if isinstance(error, anthropic.APIStatusError):
        return f"The model API returned an error ({error.status_code}): {error.message}"
    return "Could not reach the model API. Check the internet connection."


def new_conversation(phone: str, outbound):
    """Set up a fresh conversation. Nothing is sent to the model here: that
    happens only when someone presses "Start conversation" or sends a
    message, so that opening the page costs nothing."""
    st.session_state.conversation = Conversation(phone)  # its own copy of the database
    st.session_state.started_as = (phone, outbound)
    st.session_state.transcript = []  # (role, text, tool events) to display
    st.session_state.turns = 0
    st.session_state.notice = None    # (kind, one line shown above the chat)
    st.session_state.opened = False   # has the bank's opening been asked for?


def bank_writes_first(phone: str, outbound: str):
    """Have the bank open the conversation, or say why it may not."""
    st.session_state.opened = True
    try:
        with st.spinner("Escribiendo..."):
            opening = st.session_state.conversation.open(outbound)
        st.session_state.transcript.append(("assistant", opening, []))
    except OutboundNotAllowed as e:
        who = FIRST_NAMES.get(phone)
        st.session_state.notice = ("info", (
            f"The bank did not write{' to ' + who if who else ''}: {e}. Switch to "
            f"'{CUSTOMER_FIRST}' to "
            + ("see the customer ask about it." if who else "write from this number.")))
    except anthropic.APIError as e:
        st.session_state.notice = ("error", api_problem(e))


def use_default_start():
    st.session_state.start = DEFAULT_START[st.session_state.customer]


with st.sidebar:
    st.header("Demo controls")
    label = st.selectbox("Chat is coming from", list(PHONES), key="customer",
                         on_change=use_default_start)
    if "start" not in st.session_state:
        use_default_start()
    phone = PHONES[label]
    outbound = STARTS[st.selectbox("Conversation starts with", list(STARTS), key="start")]
    if st.session_state.get("started_as") != (phone, outbound):
        new_conversation(phone, outbound)
    if st.button("Reset conversation and data"):
        new_conversation(phone, outbound)

    conversation = st.session_state.conversation
    session = conversation.session
    st.subheader("Outcome")
    for item, text in conversation.outcome_summary().items():
        st.write(f"**{item}:** {shown(text)}")
    st.caption("What the conversation has recorded so far, read from its database after "
               f"every reply. Failed verification attempts: {session.failed_attempts} of "
               f"{config.MAX_VERIFICATION_ATTEMPTS}.")
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
                st.error(shown(f"Refused: {e['result']}"))
            else:
                st.success(shown(e["result"]))


st.title(f"{config.BANK_NAME} · Asistente virtual")

if outbound and not st.session_state.opened:
    st.write(f"The bank is set to write first ({outbound}) to "
             f"{FIRST_NAMES.get(phone, 'this number')}.")
    if st.button("Start conversation", type="primary"):
        bank_writes_first(phone, outbound)
        st.rerun()

if st.session_state.notice:
    kind, line = st.session_state.notice
    (st.error if kind == "error" else st.info)(shown(line))

for role, text, events in st.session_state.transcript:
    with st.chat_message(role):
        st.write(shown(text))
        show_tool_events(events)

# When the bank is to write first, the customer can only answer once it has.
user_text = st.chat_input("Escriba su mensaje",
                          disabled=bool(outbound) and not st.session_state.transcript)
if user_text:
    if st.session_state.turns >= config.MAX_TURNS_PER_SESSION:
        st.warning("Session limit reached. Use the reset button to start again.")
        st.stop()
    st.session_state.turns += 1
    st.session_state.transcript.append(("user", user_text, []))
    st.chat_message("user").write(shown(user_text))

    events_before = len(conversation.log.events)
    try:
        with st.spinner("Escribiendo..."):
            reply = conversation.send(user_text)
    except anthropic.APIError as e:
        st.error(api_problem(e))
        st.stop()

    new_events = conversation.log.events[events_before:]
    st.session_state.transcript.append(("assistant", reply, new_events))
    st.rerun()  # redraw so the sidebar shows the updated outcome

"""Core policy tests: identity, handoff, the tool doorway and the rules
for the bank starting a conversation.

These call the tools directly, with no model involved, so they prove the
rules hold in code regardless of what the rulebook says. Run every test
with: python -m tests.run
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import config
from tests.helpers import UNKNOWN_PHONE, new_conversation, verify  # keep first: freezes the date

from core import clock
from core.conversation import OutboundNotAllowed

WRONG = {"date_of_birth": "1990-01-01", "account_last4": "0000"}
HANDOFF = {"reason": "customer_request", "summary": "El cliente pide hablar con una persona."}


def test_data_is_locked_before_verification():
    c = new_conversation("maria")
    text, is_error = c.call_tool("get_customer_profile", {})
    assert is_error and "not verified" in text


def test_correct_details_verify_and_unlock_data():
    c = new_conversation("maria")
    _, is_error = verify(c, "maria")
    assert not is_error and c.session.verified
    text, is_error = c.call_tool("get_customer_profile", {})
    assert not is_error and "Guardadito" in text


def test_another_customers_details_do_not_verify():
    # Real details, but for a different customer than the phone's owner.
    c = new_conversation("maria")
    _, is_error = verify(c, "jose")
    assert is_error and not c.session.verified


def test_unknown_phone_can_never_verify():
    c = new_conversation(UNKNOWN_PHONE)
    _, is_error = verify(c, "maria")
    assert is_error and not c.session.verified


def test_verification_locks_after_max_attempts():
    c = new_conversation("maria")
    for _ in range(config.MAX_VERIFICATION_ATTEMPTS):
        c.call_tool("verify_identity", WRONG)
    # Even the correct details are now refused.
    text, is_error = verify(c, "maria")
    assert is_error and "locked" in text and not c.session.verified


def test_malformed_input_does_not_use_up_an_attempt():
    c = new_conversation("maria")
    _, is_error = c.call_tool("verify_identity", {
        "date_of_birth": "14 de marzo", "account_last4": "1234"})
    assert is_error and c.session.failed_attempts == 0


def test_handoff_creates_ticket_and_blocks_further_actions():
    c = new_conversation("maria", verified=True)
    text, is_error = c.call_tool("handoff_to_human", HANDOFF)
    assert not is_error and "HT-0001" in text and c.session.handed_off
    tickets = c.conn.execute("SELECT * FROM handoff_tickets").fetchall()
    assert len(tickets) == 1 and tickets[0]["reason"] == "customer_request"
    _, is_error = c.call_tool("get_customer_profile", {})
    assert is_error


def test_handoff_works_without_verification():
    c = new_conversation("maria")
    _, is_error = c.call_tool("handoff_to_human", HANDOFF)
    assert not is_error


def test_third_party_handoff_ends_the_conversation_quietly():
    c = new_conversation("maria")
    text, is_error = c.call_tool("handoff_to_human", {
        "reason": "third_party", "summary": "Contestó un familiar, no el titular."})
    assert not is_error and "say goodbye" in text and "will continue" not in text
    ticket = c.conn.execute("SELECT * FROM handoff_tickets").fetchone()
    assert ticket["reason"] == "third_party" and ticket["verified"] == 0


def test_unexpected_input_fields_are_rejected():
    c = new_conversation("maria", verified=True)
    _, is_error = c.call_tool("get_customer_profile", {"customer_id": 2})
    assert is_error


# --- Outbound contact ---

def at_hour(hour):
    """Make the clock report this hour, in the bank's time zone."""
    clock.now = lambda: datetime(2026, 10, 2, hour, 30, tzinfo=ZoneInfo(config.TIME_ZONE))


def opening_refusal(c):
    try:
        c.opening_note(config.ENABLED_MODULES[0])
    except OutboundNotAllowed as e:
        return str(e)
    return None


def test_clock_runs_on_the_configured_time_zone():
    assert str(clock.now().tzinfo) == config.TIME_ZONE == "America/Mexico_City"


def test_opening_note_gives_the_first_name_only():
    note = new_conversation("jose").opening_note(config.ENABLED_MODULES[0])
    assert "José Luis" in note
    assert "Ramírez" not in note and "Torres" not in note


def test_bank_cannot_open_a_conversation_with_an_unknown_number():
    assert "does not belong" in opening_refusal(new_conversation(UNKNOWN_PHONE))


def test_contact_hours_are_not_enforced_unless_switched_on():
    real_now = clock.now
    try:
        at_hour(23)
        assert not clock.within_contact_hours()
        assert opening_refusal(new_conversation("jose")) is None
    finally:
        clock.now = real_now


def test_contact_hours_block_outbound_when_switched_on():
    real_now = clock.now
    config.ENFORCE_CONTACT_HOURS = True
    try:
        for hour, allowed in ((6, False), (7, True), (20, True), (21, False)):
            at_hour(hour)
            refusal = opening_refusal(new_conversation("jose"))
            assert (refusal is None) == allowed, f"wrong answer at {hour}:30"
            assert allowed or "contact hours" in refusal
    finally:
        config.ENFORCE_CONTACT_HOURS = False
        clock.now = real_now



def test_agent_is_told_the_time_of_day():
    from core import rulebook

    real_now = clock.now
    try:
        at_hour(17)
        assert "The time is 17:30 (America/Mexico_City)" in rulebook.build_system_prompt()
    finally:
        clock.now = real_now


def test_logs_and_tickets_are_stamped_in_the_bank_time_zone():
    real_now = clock.now
    try:
        at_hour(17)
        c = new_conversation("maria")
        c.call_tool("handoff_to_human", HANDOFF)
        assert c.log.session_id.startswith("20261002-1730")
        assert c.log.events[-1]["ts"] == "2026-10-02T17:30:00"
        ticket = c.conn.execute("SELECT created_at FROM handoff_tickets").fetchone()
        assert ticket["created_at"] == "2026-10-02T17:30:00"
    finally:
        clock.now = real_now


def test_every_seed_customer_has_a_demo_start_that_exists():
    from data.seed import CUSTOMERS

    for customer in CUSTOMERS:
        assert customer["demo_start"] in (None, *config.ENABLED_MODULES), customer["first_name"]


# --- The chat screen: no model call unless someone asks for one ---

class FakeReply:
    """What the model API returns, reduced to what the agent loop reads."""
    stop_reason = "end_turn"

    def __init__(self):
        self.content = [type("Block", (), {"type": "text", "text": "Buenas tardes."})()]


def chat_screen(run):
    """Run the chat screen with a passcode set and the model replaced by a
    counter. `run(page, calls)` drives it; `calls` is every model call made."""
    import os

    from streamlit.testing.v1 import AppTest

    from core import agent

    calls, real_call = [], agent._call_model
    agent._call_model = lambda *args, **kwargs: calls.append(1) or FakeReply()
    saved = {name: os.environ.get(name) for name in ("APP_PASSCODE", "ANTHROPIC_API_KEY")}
    os.environ.update(APP_PASSCODE="test-passcode", ANTHROPIC_API_KEY="not-a-real-key")
    try:
        page = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                              "app.py"), default_timeout=60)
        run(page, calls)
    finally:
        agent._call_model = real_call
        for name, value in saved.items():
            os.environ.pop(name, None) if value is None else os.environ.update({name: value})


def press(page, label):
    next(b for b in page.button if b.label == label).click().run()


def choose(page, name):
    box = page.sidebar.selectbox[0]
    box.select(next(o for o in box.options if o.startswith(name))).run()


def test_passcode_comes_before_any_conversation_or_model_call():
    def run(page, calls):
        page.run()
        assert "conversation" not in page.session_state and not page.chat_input
        page.text_input[0].input("wrong").run()
        assert "conversation" not in page.session_state and not calls
        page.text_input[0].input("test-passcode").run()
        assert "conversation" in page.session_state and not calls

    chat_screen(run)


def test_opening_the_page_and_picking_customers_calls_the_model_zero_times():
    def run(page, calls):
        page.session_state["unlocked"] = True
        page.run()
        for name in ("Miguel", "Carmen", "Ana Karen", "Rosa", "Unknown"):
            choose(page, name)
        assert not calls and not page.exception

    chat_screen(run)


def test_bank_writes_only_when_start_is_pressed():
    def run(page, calls):
        page.session_state["unlocked"] = True
        page.run()
        choose(page, "Miguel")
        assert page.chat_input[0].disabled and not calls
        press(page, "Start conversation")
        assert len(calls) == 1 and not page.chat_input[0].disabled
        assert [m.markdown[0].value for m in page.chat_message] == ["Buenas tardes."]

    chat_screen(run)


def test_refused_contact_is_explained_without_calling_the_model():
    def run(page, calls):
        page.session_state["unlocked"] = True
        page.run()
        choose(page, "Ana Karen")
        assert not page.info
        press(page, "Start conversation")
        assert not calls and page.info[0].value.startswith(
            "The bank did not write to Ana Karen: there is an active promise for")

    chat_screen(run)


def test_customer_first_starts_with_the_first_message():
    def run(page, calls):
        page.session_state["unlocked"] = True
        page.run()
        choose(page, "Rosa")
        assert not page.chat_input[0].disabled and not calls
        assert not [b for b in page.button if b.label == "Start conversation"]
        page.chat_input[0].set_value("Hola").run()
        assert len(calls) == 1

    chat_screen(run)

# --- The transcript printer ---

def test_transcript_shows_messages_and_tool_calls_in_order():
    from tools import transcript

    c = new_conversation("maria")
    c.log.record("user_message", text="Hola, quiero saber mi saldo")
    c.call_tool("get_customer_profile", {})
    verify(c, "maria")
    c.log.record("assistant_message", text="Gracias, ya confirmé su identidad.")
    c.call_tool("handoff_to_human", HANDOFF)

    text = transcript.render(transcript.read(c.log.path))
    lines = text.splitlines()
    assert lines[1].endswith("chat from +52 55 5550 0101 · use cases: payments, renewal")
    assert "Cliente: Hola, quiero saber mi saldo" in lines
    assert "Agente:  Gracias, ya confirmé su identidad." in lines
    assert "  [get_customer_profile() -> REFUSED: Identity not verified." in text
    assert '  [verify_identity(date_of_birth="1988-03-14", account_last4="1234") -> ok:' in text
    assert text.index("quiero saber mi saldo") < text.index("REFUSED") < text.index("ya confirmé")
    assert lines[-1].startswith("Recorded: handoff (reason=customer_request")


def test_transcript_cuts_long_results_unless_asked_for_all():
    from tools import transcript

    c = new_conversation("jose", verified=True)
    c.call_tool("get_loan_status", {})
    short = transcript.render(c.log.events)
    full = transcript.render(c.log.events, full=True)
    assert "promise_limits" not in short and "promise_limits" in full


# --- The assumptions list ---

def test_assumptions_list_is_up_to_date_with_config():
    from tools import assumptions

    with open(assumptions.OUTPUT_FILE, encoding="utf-8") as f:
        assert f.read() == assumptions.render(), (
            "config.py changed: run python -m tools.assumptions --write")


def test_assumptions_list_covers_every_setting_and_labels_it():
    from tools import assumptions

    found = assumptions.entries()
    named = {e["name"]: e["kind"] for e in found if e["name"]}
    assert set(named) == {name for name in vars(config) if name.isupper()}
    assert named["REGULARIZATION_MIN_MISSED"] == "Bank doc"
    assert named["ON_TIME_DISCOUNT_PERCENT"] == "Assumption"
    assert named["MODEL"] == "Setting"
    assert all(e["note"] for e in found), "a setting has no note"

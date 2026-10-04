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

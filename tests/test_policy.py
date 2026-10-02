"""Core policy tests: identity, handoff and the tool doorway.

These call the tools directly, with no model involved, so they prove the
rules hold in code regardless of what the rulebook says. Run every test
with: python -m tests.run
"""

import config
from tests.helpers import UNKNOWN_PHONE, new_conversation, verify

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


def test_unexpected_input_fields_are_rejected():
    c = new_conversation("maria", verified=True)
    _, is_error = c.call_tool("get_customer_profile", {"customer_id": 2})
    assert is_error

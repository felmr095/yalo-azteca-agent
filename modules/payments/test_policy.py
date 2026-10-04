"""Payment assistant policy tests: the rules for promises, the catch-up
offer, the collections hold and outbound contact, checked without the model.

Tests run with today frozen, so José is always 12 days late: 520.00 overdue
plus 12.48 late interest, 532.48 in total. His weekly payment is 260.00.
"""

import json

import config
from core.conversation import OutboundNotAllowed
from tests.helpers import in_days, new_conversation


def promise(c, amount, days):
    return c.call_tool("register_payment_promise",
                       {"amount": amount, "promised_date": in_days(days)})


def regularize(c, days):
    return c.call_tool("accept_regularization_offer", {"pay_by_date": in_days(days)})


def status(c):
    text, is_error = c.call_tool("get_loan_status", {})
    assert not is_error
    return json.loads(text)


def options(c):
    text, is_error = c.call_tool("get_payment_options", {})
    assert not is_error
    return json.loads(text)


def active_promises(c):
    return c.conn.execute(
        "SELECT * FROM payment_promises WHERE status = 'active' AND loan_id ="
        " (SELECT id FROM loans WHERE customer_id = ?)", (c.session.customer_id,)
    ).fetchall()


def outbound_refusal(c):
    """Why the bank may not start a payments conversation, or None if it may."""
    try:
        c.opening_note("payments")
    except OutboundNotAllowed as e:
        return str(e)
    return None


# --- Loan status ---

def test_loan_status_is_locked_before_verification():
    c = new_conversation("jose")
    _, is_error = c.call_tool("get_loan_status", {})
    assert is_error


def test_loan_status_adds_late_interest_to_the_overdue_amount():
    loan = status(new_conversation("jose", verified=True))
    assert loan["days_late"] == 12 and loan["amount_overdue"] == 520
    assert loan["late_interest"] == 12.48 and loan["total_overdue"] == 532.48


def test_loan_status_for_a_customer_who_is_up_to_date():
    loan = status(new_conversation("maria", verified=True))
    assert loan["days_late"] == 0 and loan["days_until_due"] == 4
    assert loan["late_interest"] == 0 and loan["promise_limits"] is None


# --- Payment promises ---

def test_promise_is_locked_before_verification():
    c = new_conversation("jose")
    _, is_error = promise(c, 300, 7)
    assert is_error and not active_promises(c)


def test_valid_promise_is_registered():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 300, 7)
    assert not is_error and "SPEI" in text
    assert len(active_promises(c)) == 1
    assert active_promises(c)[0]["amount"] == 300 and active_promises(c)[0]["kind"] == "promise"


def test_promise_on_the_last_allowed_day_is_accepted():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 300, config.PROMISE_MAX_DAYS)
    assert not is_error


def test_promise_beyond_the_window_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 300, config.PROMISE_MAX_DAYS + 1)
    assert is_error and "too far" in text and not active_promises(c)


def test_promise_in_the_past_is_refused():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 300, -1)
    assert is_error and not active_promises(c)


def test_promise_of_one_weekly_payment_is_accepted():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 260, 7)
    assert not is_error


def test_promise_below_one_weekly_payment_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 259, 7)
    assert is_error and "260.00" in text and not active_promises(c)


def test_promise_of_the_total_overdue_is_accepted():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 532.48, 7)
    assert not is_error


def test_promise_above_the_total_overdue_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 533, 7)
    assert is_error and "532.48" in text and not active_promises(c)


def test_second_promise_is_refused_while_one_is_active():
    c = new_conversation("jose", verified=True)
    promise(c, 300, 7)
    _, is_error = promise(c, 300, 10)
    assert is_error and len(active_promises(c)) == 1


def test_seeded_active_promise_blocks_a_new_one():
    c = new_conversation("ana", verified=True)
    _, is_error = promise(c, 410, 7)
    assert is_error and len(active_promises(c)) == 1


def test_one_broken_promise_still_allows_a_new_one():
    c = new_conversation("miguel", verified=True)
    _, is_error = promise(c, 1040, 7)
    assert not is_error


def test_two_broken_promises_require_a_handoff():
    c = new_conversation("juan", verified=True)
    text, is_error = promise(c, 900, 7)
    assert is_error and "policy_limit" in text and not active_promises(c)


def test_customer_who_is_current_cannot_register_a_promise():
    c = new_conversation("maria", verified=True)
    _, is_error = promise(c, 320, 7)
    assert is_error


def test_customer_without_a_loan_cannot_register_a_promise():
    c = new_conversation("rosa", verified=True)
    _, is_error = promise(c, 100, 7)
    assert is_error


def test_no_promise_after_handoff():
    c = new_conversation("jose", verified=True)
    c.call_tool("handoff_to_human", {"reason": "hardship", "summary": "Perdió su empleo."})
    _, is_error = promise(c, 300, 7)
    assert is_error and not active_promises(c)


# --- Payment options ---

def test_payment_options_before_verification_show_channels_but_no_amounts():
    c = new_conversation("jose")
    found = options(c)
    assert "Transferencia SPEI" in found["where_to_pay"] and found["amounts"] is None


def test_payment_options_for_an_overdue_customer_include_the_offer():
    found = options(new_conversation("jose", verified=True))["amounts"]
    assert found["to_be_up_to_date"] == 532.48
    offer = found["catch_up_offer"]
    # Half of the 12.48 late interest is waived.
    assert offer["available"] and offer["late_interest_waived"] == 6.24
    assert offer["amount_to_pay"] == 526.24
    assert offer["latest_pay_by_date"] == in_days(config.REGULARIZATION_MAX_DAYS)


def test_payment_options_for_a_current_customer_show_the_next_payment():
    found = options(new_conversation("maria", verified=True))["amounts"]
    assert found == {"next_payment": {"amount": 320, "due_date": in_days(4)}}


# --- The catch-up offer ---

def test_accepted_offer_is_registered_with_the_waiver():
    c = new_conversation("jose", verified=True)
    text, is_error = regularize(c, 5)
    assert not is_error and "SPEI" in text
    row = active_promises(c)[0]
    assert row["kind"] == "regularization" and row["promised_date"] == in_days(5)
    assert row["amount"] == 526.24 and row["interest_waived"] == 6.24


def test_offer_is_locked_before_verification():
    c = new_conversation("jose")
    _, is_error = regularize(c, 5)
    assert is_error and not active_promises(c)


def test_offer_date_beyond_the_window_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = regularize(c, config.REGULARIZATION_MAX_DAYS + 1)
    assert is_error and "too far" in text and not active_promises(c)


def test_offer_is_not_available_when_only_a_few_days_late():
    # Ana is 5 days late. Remove her seeded promise so that only her
    # lateness decides.
    c = new_conversation("ana", verified=True)
    c.conn.execute("DELETE FROM payment_promises")
    text, is_error = regularize(c, 5)
    assert is_error and "5 days late" in text and not active_promises(c)
    assert options(c)["amounts"]["catch_up_offer"]["available"] is False


def test_offer_is_not_available_when_too_late():
    c = new_conversation("miguel", verified=True)
    c.conn.execute("UPDATE loans SET next_due_date = ? WHERE customer_id = ?",
                   (in_days(-(config.REGULARIZATION_MAX_DAYS_LATE + 1)), c.session.customer_id))
    text, is_error = regularize(c, 5)
    assert is_error and "policy_limit" in text and not active_promises(c)


def test_offer_is_refused_while_a_promise_is_active():
    c = new_conversation("jose", verified=True)
    promise(c, 300, 7)
    _, is_error = regularize(c, 5)
    assert is_error and len(active_promises(c)) == 1


def test_offer_is_refused_after_two_broken_promises():
    c = new_conversation("juan", verified=True)
    text, is_error = regularize(c, 5)
    assert is_error and "policy_limit" in text and not active_promises(c)


def test_offer_can_be_used_only_once_per_loan():
    c = new_conversation("jose", verified=True)
    regularize(c, 5)
    c.conn.execute("UPDATE payment_promises SET status = 'kept' WHERE kind = 'regularization'")
    text, is_error = regularize(c, 5)
    assert is_error and "only once" in text and not active_promises(c)
    # A plain promise is still possible.
    _, is_error = promise(c, 300, 7)
    assert not is_error


def test_offer_is_refused_for_a_customer_who_is_current():
    c = new_conversation("maria", verified=True)
    _, is_error = regularize(c, 5)
    assert is_error


# --- The collections hold and outbound contact ---

def test_a_commitment_places_a_collections_hold_until_its_date():
    c = new_conversation("jose", verified=True)
    assert status(c)["collections_hold_until"] is None
    promise(c, 300, 7)
    assert status(c)["collections_hold_until"] == in_days(7)


def test_bank_may_contact_an_overdue_customer():
    assert outbound_refusal(new_conversation("jose")) is None


def test_bank_may_not_contact_a_customer_during_a_hold():
    # Ana has a seeded promise for 3 days from now.
    refusal = outbound_refusal(new_conversation("ana"))
    assert refusal and "hold" in refusal and in_days(3) in refusal


def test_hold_ends_once_the_promised_date_has_passed():
    c = new_conversation("ana")
    c.conn.execute("UPDATE payment_promises SET promised_date = ? WHERE status = 'active'",
                   (in_days(-1),))
    assert outbound_refusal(c) is None


def test_bank_may_remind_a_customer_whose_payment_is_due_soon():
    # María's payment is due in 4 days.
    assert outbound_refusal(new_conversation("maria")) is None


def test_bank_may_not_remind_a_customer_whose_payment_is_far_off():
    c = new_conversation("maria")
    c.conn.execute("UPDATE loans SET next_due_date = ? WHERE customer_id = ?",
                   (in_days(config.REMINDER_DAYS_BEFORE_DUE + 1), c.session.customer_id))
    assert "Reminders start" in outbound_refusal(c)


def test_bank_may_not_contact_a_customer_without_a_loan():
    assert "no loan" in outbound_refusal(new_conversation("rosa"))


# --- Contact details ---

def test_there_is_no_tool_to_change_a_phone_number():
    c = new_conversation("jose", verified=True)
    text, is_error = c.call_tool("update_contact_phone", {"new_phone": "81 1234 5678"})
    assert is_error and "no tool" in text
    phone = c.conn.execute("SELECT phone FROM customers WHERE id = ?",
                           (c.session.customer_id,)).fetchone()["phone"]
    assert phone == "+52 81 5550 0102"

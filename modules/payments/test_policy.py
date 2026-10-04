"""Payment assistant policy tests: the rules for promises, the catch-up
program, the collections hold and outbound contact, checked without the
model.

Tests run with today frozen. José has missed 2 weekly payments (12 days
late). His payment is 270.00 on time and 300.00 standard, so he owes
600.00 plus 14.40 late interest: 614.40 in total.
"""

import json

import config
from core.conversation import OutboundNotAllowed
from tests.helpers import in_days, new_conversation


def promise(c, amount, days, offer_id=None):
    tool_input = {"amount": amount, "promised_date": in_days(days)}
    if offer_id:
        tool_input["offer_id"] = offer_id
    return c.call_tool("register_payment_promise", tool_input)


def offer(c):
    text, is_error = c.call_tool("compute_regularization_offer", {})
    assert not is_error, text
    return json.loads(text)


def offer_refusal(c):
    text, is_error = c.call_tool("compute_regularization_offer", {})
    assert is_error, "an offer was made"
    return text


def status(c):
    text, is_error = c.call_tool("get_loan_status", {})
    assert not is_error
    return json.loads(text)


def promises(c, where="1 = 1"):
    return c.conn.execute(
        f"SELECT * FROM payment_promises WHERE {where} AND loan_id ="
        " (SELECT id FROM loans WHERE customer_id = ?)", (c.session.customer_id,)
    ).fetchall()


def active_promises(c):
    return promises(c, "status = 'active'")


def set_loan(c, **fields):
    for name, value in fields.items():
        c.conn.execute(f"UPDATE loans SET {name} = ? WHERE customer_id = ?",
                       (value, c.session.customer_id))


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


def test_loan_status_for_a_late_customer():
    loan = status(new_conversation("jose", verified=True))
    assert loan["installments_missed"] == 2 and loan["days_late"] == 12
    assert loan["installment_on_time"] == 270 and loan["installment_standard"] == 300
    assert loan["on_time_discount"].startswith("lost")
    # Missed payments are owed at the standard price, plus late interest.
    assert loan["amount_overdue"] == 600 and loan["late_interest_accrued"] == 14.4
    assert loan["total_overdue"] == 614.4
    assert loan["promise_limits"]["minimum_amount"] == 270
    assert loan["promise_limits"]["maximum_amount"] == 614.4


def test_loan_status_for_a_customer_who_is_up_to_date():
    loan = status(new_conversation("maria", verified=True))
    assert loan["installments_missed"] == 0 and loan["days_late"] == 0
    assert loan["days_until_due"] == 2 and loan["next_due_date"] == in_days(2)
    assert loan["on_time_discount"] == "applies" and loan["total_overdue"] == 0


def test_loan_status_shows_the_last_payment_on_record():
    loan = status(new_conversation("jose", verified=True))
    assert loan["last_payment_on_record"]["paid_on"] == in_days(-19)


def test_loan_status_shows_whether_the_loan_is_on_a_plan():
    assert status(new_conversation("fernando", verified=True))["has_plan"] is True
    assert status(new_conversation("jose", verified=True))["has_plan"] is False


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
    assert active_promises(c)[0]["amount"] == 300 and active_promises(c)[0]["offer_id"] is None


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


def test_promise_of_one_on_time_payment_is_accepted():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 270, 7)
    assert not is_error


def test_promise_below_one_on_time_payment_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 269, 7)
    assert is_error and "270.00" in text and not active_promises(c)


def test_promise_of_the_total_overdue_is_accepted():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 614.40, 7)
    assert not is_error


def test_promise_above_the_total_overdue_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 615, 7)
    assert is_error and "614.40" in text and not active_promises(c)


def test_second_promise_is_refused_while_one_is_active():
    c = new_conversation("jose", verified=True)
    promise(c, 300, 7)
    _, is_error = promise(c, 300, 10)
    assert is_error and len(active_promises(c)) == 1


def test_seeded_active_promise_blocks_a_new_one():
    c = new_conversation("ana", verified=True)
    _, is_error = promise(c, 450, 7)
    assert is_error and len(active_promises(c)) == 1


def test_one_broken_promise_still_allows_a_new_one():
    c = new_conversation("miguel", verified=True)
    _, is_error = promise(c, 1040, 7)
    assert not is_error


def test_two_broken_promises_require_a_handoff():
    c = new_conversation("juan", verified=True)
    text, is_error = promise(c, 900, 7)
    assert is_error and "policy_limit" in text and not active_promises(c)


def test_customer_without_a_loan_cannot_register_a_promise():
    c = new_conversation("rosa", verified=True)
    _, is_error = promise(c, 100, 7)
    assert is_error


def test_no_promise_after_handoff():
    c = new_conversation("jose", verified=True)
    c.call_tool("handoff_to_human", {"reason": "hardship", "summary": "Perdió su empleo."})
    _, is_error = promise(c, 300, 7)
    assert is_error and not active_promises(c)


def test_loan_on_a_plan_can_still_register_a_promise():
    c = new_conversation("fernando", verified=True)
    _, is_error = promise(c, 360, 7)
    assert not is_error


# A customer who is up to date (María: 360.00 on time, 400.00 standard, due
# in 2 days) can promise a date after the due date, for one weekly payment.

def test_current_customer_can_promise_a_date_after_the_due_date():
    c = new_conversation("maria", verified=True)
    _, is_error = promise(c, 400, 4)
    assert not is_error and status(c)["hold_until"] == in_days(4)


def test_current_customer_needs_no_promise_up_to_the_due_date():
    c = new_conversation("maria", verified=True)
    text, is_error = promise(c, 360, 2)
    assert is_error and "No promise is needed" in text and not active_promises(c)


def test_current_customer_cannot_promise_more_than_one_weekly_payment():
    c = new_conversation("maria", verified=True)
    text, is_error = promise(c, 401, 4)
    assert is_error and "400.00" in text and not active_promises(c)


# --- The catch-up program ---

def test_offer_is_locked_before_verification():
    c = new_conversation("jose")
    _, is_error = c.call_tool("compute_regularization_offer", {})
    assert is_error


def test_offer_returns_the_five_fields_the_program_requires():
    found = offer(new_conversation("jose", verified=True))
    # Owed by the pay-by date without the program: 2 missed payments and the
    # coming one at the standard price (3 x 300.00), plus 14.40 late interest.
    assert found["amount_owed"] == 914.4
    # With it: the same 3 payments at the on-time price (3 x 270.00).
    assert found["amount_to_pay"] == 810
    assert found["amount_waived"] == 104.4
    assert found["weeks_late"] == 2
    assert found["pay_by_date"] == in_days(config.REGULARIZATION_PAY_WITHIN_DAYS)


def test_offer_always_asks_for_less_than_is_owed():
    for who in ("jose", "miguel"):
        found = offer(new_conversation(who, verified=True))
        assert found["amount_to_pay"] < found["amount_owed"]
        assert found["amount_waived"] == round(found["amount_owed"] - found["amount_to_pay"], 2)


def test_offer_for_five_missed_payments():
    found = offer(new_conversation("miguel", verified=True))
    assert found["amount_owed"] == 3786 and found["amount_waived"] == 546
    assert found["weeks_late"] == 5 and found["amount_to_pay"] == 3240


def test_computing_an_offer_commits_the_customer_to_nothing():
    c = new_conversation("jose", verified=True)
    offer(c)
    assert not promises(c)
    # It is still possible to make an ordinary promise, or to accept later.
    assert not promise(c, 300, 7)[1]


def test_no_offer_with_one_missed_payment():
    assert "at least 2" in offer_refusal(new_conversation("laura", verified=True))


def test_no_offer_for_a_customer_who_is_up_to_date():
    offer_refusal(new_conversation("maria", verified=True))


def test_offer_at_the_most_missed_payments_allowed():
    c = new_conversation("jose", verified=True)
    set_loan(c, installments_missed=config.REGULARIZATION_MAX_MISSED)
    assert offer(c)["weeks_late"] == config.REGULARIZATION_MAX_MISSED


def test_no_offer_beyond_the_most_missed_payments_allowed():
    c = new_conversation("jose", verified=True)
    set_loan(c, installments_missed=config.REGULARIZATION_MAX_MISSED + 1)
    assert "policy_limit" in offer_refusal(c)


def test_no_offer_for_a_loan_on_a_plan():
    assert "on a plan" in offer_refusal(new_conversation("fernando", verified=True))


def test_no_offer_after_two_broken_promises():
    assert "policy_limit" in offer_refusal(new_conversation("juan", verified=True))


def test_no_offer_while_a_promise_is_active():
    c = new_conversation("jose", verified=True)
    promise(c, 300, 7)
    assert "active" in offer_refusal(c)


def test_accepted_offer_is_a_promise_for_its_full_amount():
    c = new_conversation("jose", verified=True)
    found = offer(c)
    text, is_error = promise(c, 810, 5, found["offer_id"])
    assert not is_error and "cajero" in text and "SPEI" in text
    row = active_promises(c)[0]
    assert row["offer_id"] == found["offer_id"] and row["amount"] == 810
    assert row["amount_waived"] == 104.4 and row["promised_date"] == in_days(5)
    assert status(c)["hold_until"] == in_days(5)


def test_offer_cannot_be_accepted_for_another_amount():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 600, 5, offer(c)["offer_id"])
    assert is_error and "810.00" in text and not active_promises(c)


def test_offer_cannot_be_accepted_for_a_date_after_its_pay_by_date():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 810, config.REGULARIZATION_PAY_WITHIN_DAYS + 1,
                             offer(c)["offer_id"])
    assert is_error and "too far" in text and not active_promises(c)


def test_made_up_offer_id_is_refused():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 810, 5, "PAC-9999-20260101")
    assert is_error and not active_promises(c)


def test_offer_id_does_not_work_for_a_loan_that_does_not_qualify():
    c = new_conversation("fernando", verified=True)
    _, is_error = promise(c, 1440, 5, "PAC-0006-" + in_days(0).replace("-", ""))
    assert is_error and not active_promises(c)


def test_offer_can_be_used_only_once_per_loan():
    c = new_conversation("jose", verified=True)
    promise(c, 810, 5, offer(c)["offer_id"])
    c.conn.execute("UPDATE payment_promises SET status = 'kept' WHERE offer_id IS NOT NULL")
    assert "only once" in offer_refusal(c)
    # An ordinary promise is still possible.
    _, is_error = promise(c, 300, 7)
    assert not is_error


# --- The collections hold and outbound contact ---

def test_a_promise_places_a_collections_hold_until_its_date():
    c = new_conversation("jose", verified=True)
    assert status(c)["hold_until"] is None
    promise(c, 300, 7)
    assert status(c)["hold_until"] == in_days(7)


def test_bank_may_contact_a_late_customer():
    assert outbound_refusal(new_conversation("jose")) is None


def test_bank_may_not_contact_a_customer_during_a_hold():
    # Ana has a seeded promise for 3 days from now.
    refusal = outbound_refusal(new_conversation("ana"))
    assert refusal == ("there is an active promise for $450.00 due 5 October, and the hold "
                       "suppresses contact until then")


def test_hold_ends_once_the_promised_date_has_passed():
    c = new_conversation("ana")
    c.conn.execute("UPDATE payment_promises SET promised_date = ? WHERE status = 'active'",
                   (in_days(-1),))
    assert outbound_refusal(c) is None


def test_bank_may_remind_a_customer_whose_payment_is_due_soon():
    # María's payment is due in 2 days.
    assert outbound_refusal(new_conversation("maria")) is None


def test_bank_may_not_remind_a_customer_whose_payment_is_far_off():
    c = new_conversation("maria")
    set_loan(c, next_due_date=in_days(config.REMINDER_DAYS_BEFORE_DUE + 1))
    assert "reminders start" in outbound_refusal(c)


def test_bank_may_not_contact_a_customer_without_a_loan():
    assert "no loan" in outbound_refusal(new_conversation("rosa"))


# --- The outcome summary ---

def test_outcome_shows_nothing_before_anything_happens():
    found = new_conversation("jose").outcome_summary()
    assert found["Opening"] == "the customer writes first"
    assert found["Identity"] == "not verified" and found["Handoff"] == "none"
    assert found["Promise"] == "none" and found["Offer shown"] == "none"


def test_outcome_shows_an_offer_that_was_shown_but_not_accepted():
    c = new_conversation("jose", verified=True)
    offer(c)
    found = c.outcome_summary()
    assert found["Identity"] == "verified" and found["Promise"] == "none"
    assert found["Offer shown"] == (
        f"Ponte al corriente: owes $914.40, waived $104.40, pays $810.00 by {in_days(7)} "
        "(not accepted)")


def test_outcome_shows_an_accepted_offer_as_a_promise_with_its_hold():
    c = new_conversation("jose", verified=True)
    promise(c, 810, 5, offer(c)["offer_id"])
    found = c.outcome_summary()
    assert found["Promise"] == (
        f"$810.00 on {in_days(5)}, hold until {in_days(5)}, under Ponte al corriente "
        "(made in this conversation)")
    assert found["Offer shown"].endswith("(accepted)")


def test_outcome_tells_an_earlier_promise_from_a_new_one():
    found = new_conversation("ana").outcome_summary()
    assert found["Promise"] == f"$450.00 on {in_days(3)}, hold until {in_days(3)} (made earlier)"


def test_outcome_shows_why_the_bank_did_not_write():
    c = new_conversation("ana")
    try:
        c.open("payments")   # refused before any model call
    except OutboundNotAllowed:
        pass
    assert c.outcome_summary()["Opening"] == (
        "the bank did not write (payments): there is an active promise for $450.00 due "
        "5 October, and the hold suppresses contact until then")


def test_outcome_shows_the_handoff_ticket_and_reason():
    c = new_conversation("miguel", verified=True)
    c.call_tool("handoff_to_human", {"reason": "hardship", "summary": "Perdió su empleo."})
    found = c.outcome_summary()
    assert found["Handoff"] == "ticket HT-0001, reason hardship" and found["Promise"] == "none"


# --- Where to pay, and contact details ---

def test_where_to_pay_needs_no_verification_and_reveals_nothing():
    unverified, _ = new_conversation("jose").call_tool("get_payment_options", {})
    verified, _ = new_conversation("jose", verified=True).call_tool("get_payment_options", {})
    assert unverified == verified
    found = json.loads(unverified)
    assert found["where_to_pay"] == config.PAYMENT_CHANNELS and len(found["where_to_pay"]) == 4
    assert "cajero" in unverified


def test_there_is_no_tool_to_change_a_phone_number():
    c = new_conversation("jose", verified=True)
    text, is_error = c.call_tool("update_contact_phone", {"new_phone": "81 1234 5678"})
    assert is_error and "no tool" in text
    phone = c.conn.execute("SELECT phone FROM customers WHERE id = ?",
                           (c.session.customer_id,)).fetchone()["phone"]
    assert phone == "+52 81 5550 0102"

"""Renewal policy tests: who may be offered a loan, what may be quoted, and
how an application starts, checked without the model.

Carmen has made 45 of her 52 payments, all on time, and is pre-approved for
8,000.00 pesos. Ricardo has as good a record but an active payment promise.
Sofía qualifies but declined the offer 10 days ago.
"""

import json

import config
from core.conversation import OutboundNotAllowed
from tests.helpers import in_days, new_conversation


def eligibility(c):
    text, is_error = c.call_tool("get_renewal_eligibility", {})
    assert not is_error, text
    return json.loads(text)


def quote(c, amount=5000, term_weeks=52):
    return c.call_tool("quote_loan", {"amount": amount, "term_weeks": term_weeks})


def apply(c, amount=5000, term_weeks=52):
    return c.call_tool("start_loan_application", {"amount": amount, "term_weeks": term_weeks})


def applications(c):
    return c.conn.execute("SELECT * FROM loan_applications").fetchall()


def set_profile(c, **fields):
    for name, value in fields.items():
        c.conn.execute(
            f"UPDATE renewal_profiles SET {name} = ? WHERE loan_id ="
            " (SELECT id FROM loans WHERE customer_id = ?)", (value, c.session.customer_id))


def add_promise(c, status, created_days_ago):
    c.conn.execute(
        "INSERT INTO payment_promises (loan_id, amount, promised_date, status, created_on)"
        " VALUES ((SELECT id FROM loans WHERE customer_id = ?), 300, ?, ?, ?)",
        (c.session.customer_id, in_days(7 - created_days_ago), status, in_days(-created_days_ago)))


def outbound_refusal(c):
    """Why the bank may not start a renewal conversation, or None if it may."""
    try:
        c.opening_note("renewal")
    except OutboundNotAllowed as e:
        return str(e)
    return None


# --- Nothing before verification ---

def test_every_renewal_tool_is_locked_before_verification():
    c = new_conversation("carmen")
    for tool, tool_input in (("get_renewal_eligibility", {}), ("record_offer_decline", {}),
                             ("quote_loan", {"amount": 5000, "term_weeks": 52}),
                             ("start_loan_application", {"amount": 5000, "term_weeks": 52})):
        text, is_error = c.call_tool(tool, tool_input)
        assert is_error and "not verified" in text, tool
    assert not applications(c)


# --- Who qualifies ---

def test_customer_with_a_good_record_qualifies():
    found = eligibility(new_conversation("carmen", verified=True))
    assert found["eligible"] and found["preapproved_max"] == 8000
    assert found["on_time_percent"] == 100 and found["share_repaid_percent"] == 86.5
    assert found["minimum_amount"] == 2000 and found["terms_weeks"] == [26, 39, 52]


def test_on_time_record_below_the_minimum_does_not_qualify():
    c = new_conversation("carmen", verified=True)
    set_profile(c, installments_on_time=40)   # 40 of 45: 88.9%
    found = eligibility(c)
    assert not found["eligible"] and "preapproved_max" not in found


def test_recent_late_payment_does_not_qualify():
    c = new_conversation("carmen", verified=True)
    set_profile(c, installments_on_time=44,
                last_late_payment_on=in_days(-7 * config.RENEWAL_NO_LATE_WEEKS + 1))
    assert not eligibility(c)["eligible"]
    set_profile(c, last_late_payment_on=in_days(-7 * config.RENEWAL_NO_LATE_WEEKS))
    assert eligibility(c)["eligible"]


def test_loan_not_repaid_enough_does_not_qualify():
    c = new_conversation("carmen", verified=True)
    set_profile(c, installments_paid=38, installments_on_time=38)   # 38 of 52: 73.1%
    assert not eligibility(c)["eligible"]
    set_profile(c, installments_paid=39, installments_on_time=39)   # 75%
    assert eligibility(c)["eligible"]


def test_recent_payment_promise_does_not_qualify_even_if_kept():
    c = new_conversation("carmen", verified=True)
    add_promise(c, "kept", created_days_ago=30 * config.RENEWAL_NO_PROMISE_MONTHS - 1)
    assert not eligibility(c)["eligible"]


def test_old_payment_promise_does_not_count():
    c = new_conversation("carmen", verified=True)
    add_promise(c, "kept", created_days_ago=30 * config.RENEWAL_NO_PROMISE_MONTHS + 1)
    assert eligibility(c)["eligible"]


def test_customer_without_a_pre_approved_offer_does_not_qualify():
    assert not eligibility(new_conversation("maria", verified=True))["eligible"]


# --- Never credit for a customer who is late or has an active promise ---

def test_customer_with_an_active_promise_is_never_offered_credit():
    c = new_conversation("ricardo", verified=True)
    found = eligibility(c)
    assert not found["eligible"] and "Do not offer" in found["instruction"]
    for attempt in (quote, apply):
        text, is_error = attempt(c, 3000, 52)
        assert is_error and "Do not offer" in text
    assert not applications(c) and "active payment promise" in outbound_refusal(c)


def test_customer_who_is_late_is_never_offered_credit():
    c = new_conversation("carmen", verified=True)
    c.conn.execute("UPDATE loans SET installments_missed = 1 WHERE customer_id = ?",
                   (c.session.customer_id,))
    assert "Do not offer" in eligibility(c)["instruction"]
    text, is_error = quote(c)
    assert is_error and "missed payments" in text
    assert "missed payments" in outbound_refusal(c)


def test_application_is_refused_if_the_customer_falls_behind_after_the_quote():
    c = new_conversation("carmen", verified=True)
    quote(c)
    c.conn.execute("UPDATE loans SET installments_missed = 1 WHERE customer_id = ?",
                   (c.session.customer_id,))
    _, is_error = apply(c)
    assert is_error and not applications(c)


# --- Quotes ---

def test_quote_gives_weekly_payment_total_and_cat():
    text, is_error = quote(new_conversation("carmen", verified=True), 5000, 52)
    found = json.loads(text)
    assert not is_error and found["weekly_payment"] == 122.42
    assert found["total_to_pay"] == 6365.84 and found["total_interest"] == 1365.84
    assert found["annual_interest_rate_percent"] == 49.62 and found["cat_percent"] == 83.5


def test_shorter_term_costs_more_per_week_and_less_in_total():
    c = new_conversation("carmen", verified=True)
    short, long = json.loads(quote(c, 5000, 26)[0]), json.loads(quote(c, 5000, 52)[0])
    assert short["weekly_payment"] > long["weekly_payment"]
    assert short["total_to_pay"] < long["total_to_pay"]


def test_quote_at_the_limits_is_accepted():
    c = new_conversation("carmen", verified=True)
    assert not quote(c, config.RENEWAL_MIN_AMOUNT, 26)[1] and not quote(c, 8000, 52)[1]


def test_quote_below_the_smallest_loan_is_refused():
    text, is_error = quote(new_conversation("carmen", verified=True), 1999, 52)
    assert is_error and "2000.00" in text


def test_quote_above_the_pre_approved_limit_is_refused():
    text, is_error = quote(new_conversation("carmen", verified=True), 15000, 52)
    assert is_error and "8000.00" in text


def test_quote_for_a_term_not_on_offer_is_refused():
    _, is_error = quote(new_conversation("carmen", verified=True), 5000, 30)
    assert is_error


# --- Applications ---

def test_application_needs_a_quote_first():
    c = new_conversation("carmen", verified=True)
    text, is_error = apply(c)
    assert is_error and "quote_loan first" in text and not applications(c)


def test_application_must_match_what_was_quoted():
    c = new_conversation("carmen", verified=True)
    quote(c, 5000, 52)
    for amount, term in ((6000, 52), (5000, 26)):
        _, is_error = apply(c, amount, term)
        assert is_error
    assert not applications(c)


def test_application_is_started_and_awaits_confirmation_in_the_app():
    c = new_conversation("carmen", verified=True)
    quote(c)
    text, is_error = apply(c)
    found = json.loads(text)
    assert not is_error and found["reference"].startswith("SOL-")
    assert found["status"] == "iniciada, pendiente de confirmación en la app"
    row = applications(c)[0]
    assert row["amount"] == 5000 and row["term_weeks"] == 52 and row["weekly_payment"] == 122.42
    assert row["reference"] == found["reference"] and row["status"] == found["status"]


def test_only_one_application_at_a_time():
    c = new_conversation("carmen", verified=True)
    quote(c)
    apply(c)
    text, is_error = apply(c)
    assert is_error and "already started" in text and len(applications(c)) == 1


# --- The outcome summary ---

def test_outcome_shows_the_quote_and_the_application():
    c = new_conversation("carmen", verified=True)
    assert c.outcome_summary()["Loan quoted"] == "none"
    quote(c)
    found = c.outcome_summary()
    assert found["Loan quoted"] == "$5,000.00 over 52 weeks: $122.42 a week, $6,365.84 in total"
    assert found["Loan application"] == "none" and found["Loan offer declined"] == "no"
    reference = json.loads(apply(c)[0])["reference"]
    assert c.outcome_summary()["Loan application"] == (
        f"{reference}: $5,000.00 over 52 weeks, iniciada, pendiente de confirmación en la app")


def test_outcome_shows_a_decline():
    c = new_conversation("carmen", verified=True)
    c.call_tool("record_offer_decline", {})
    assert c.outcome_summary()["Loan offer declined"] == (
        f"yes, on {in_days(0)}; no new offer before {in_days(config.RENEWAL_REOFFER_DAYS)}")


# --- Declines and how often the bank may offer ---

def test_bank_may_offer_a_loan_to_a_customer_who_qualifies():
    assert outbound_refusal(new_conversation("carmen")) is None


def test_bank_may_not_offer_to_customers_who_do_not_qualify():
    for who in ("jose", "maria", "rosa"):
        assert outbound_refusal(new_conversation(who)), who


def test_decline_is_recorded_and_stops_new_offers():
    c = new_conversation("carmen", verified=True)
    text, is_error = c.call_tool("record_offer_decline", {})
    assert not is_error
    assert json.loads(text)["no_new_offer_before"] == in_days(config.RENEWAL_REOFFER_DAYS)
    assert len(c.conn.execute("SELECT * FROM renewal_declines WHERE customer_id = ?",
                              (c.session.customer_id,)).fetchall()) == 1
    assert outbound_refusal(c) == (
        f"the customer declined an offer 0 days ago; no new offer for "
        f"{config.RENEWAL_REOFFER_DAYS} more days")


def test_bank_may_not_offer_again_within_the_waiting_period():
    # Sofía declined 10 days ago.
    c = new_conversation("sofia", verified=True)
    assert outbound_refusal(c) == (
        f"the customer declined an offer 10 days ago; no new offer for "
        f"{config.RENEWAL_REOFFER_DAYS - 10} more days")
    # She may still ask for a loan herself.
    found = eligibility(c)
    assert found["eligible"] and "recently_declined_or_applied" in found
    assert not quote(c, 3000, 26)[1]


def test_bank_may_offer_again_after_the_waiting_period():
    c = new_conversation("sofia")
    c.conn.execute("UPDATE renewal_declines SET declined_on = ?",
                   (in_days(-config.RENEWAL_REOFFER_DAYS),))
    assert outbound_refusal(c) is None


def test_started_application_also_stops_new_offers():
    c = new_conversation("carmen", verified=True)
    quote(c)
    apply(c)
    assert "started an application" in outbound_refusal(c)

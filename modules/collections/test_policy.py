"""Collections policy tests: the promise rules, checked without the model."""

from tests.helpers import in_days, new_conversation


def promise(c, amount, days):
    return c.call_tool("register_payment_promise",
                       {"amount": amount, "promised_date": in_days(days)})


def active_promises(c):
    return c.conn.execute(
        "SELECT * FROM payment_promises WHERE status = 'active' AND loan_id ="
        " (SELECT id FROM loans WHERE customer_id = ?)", (c.session.customer_id,)
    ).fetchall()


def test_loan_status_is_locked_before_verification():
    c = new_conversation("jose")
    _, is_error = c.call_tool("get_loan_status", {})
    assert is_error


def test_promise_is_locked_before_verification():
    c = new_conversation("jose")
    _, is_error = promise(c, 300, 7)
    assert is_error and not active_promises(c)


def test_valid_promise_is_registered():
    # José owes 520 overdue, so the minimum is 260.
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 300, 7)
    assert not is_error and "Elektra" in text
    assert len(active_promises(c)) == 1 and active_promises(c)[0]["amount"] == 300


def test_promise_on_the_last_allowed_day_is_accepted():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 300, 15)
    assert not is_error


def test_promise_beyond_the_window_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 300, 16)
    assert is_error and "too far" in text and not active_promises(c)


def test_promise_in_the_past_is_refused():
    c = new_conversation("jose", verified=True)
    _, is_error = promise(c, 300, -1)
    assert is_error and not active_promises(c)


def test_promise_below_the_minimum_is_refused():
    c = new_conversation("jose", verified=True)
    text, is_error = promise(c, 259, 7)
    assert is_error and "260.00" in text and not active_promises(c)


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


def test_phone_update_accepts_a_valid_number():
    c = new_conversation("jose", verified=True)
    text, is_error = c.call_tool("update_contact_phone", {"new_phone": "81 1234 5678"})
    assert not is_error and "+52 8112345678" in text


def test_phone_update_rejects_a_short_number():
    c = new_conversation("jose", verified=True)
    _, is_error = c.call_tool("update_contact_phone", {"new_phone": "12345"})
    assert is_error


def test_phone_update_rejects_another_customers_number():
    c = new_conversation("jose", verified=True)
    _, is_error = c.call_tool("update_contact_phone", {"new_phone": "55 5550 0101"})
    assert is_error

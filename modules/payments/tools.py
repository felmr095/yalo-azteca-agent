"""Payment assistant tools. Every policy number comes from config.py and is
enforced here, whatever the rulebook or the customer says."""

from datetime import date, timedelta
from typing import Optional

import config
from core.clock import plain_date, today
from core.tools import Tool, ToolError


def _loan(conn, customer_id):
    return conn.execute("SELECT * FROM loans WHERE customer_id = ?", (customer_id,)).fetchone()


def _promises(conn, loan_id, status):
    return conn.execute(
        "SELECT * FROM payment_promises WHERE loan_id = ? AND status = ? ORDER BY promised_date",
        (loan_id, status),
    ).fetchall()


def _days_until_due(loan) -> int:
    return (date.fromisoformat(loan["next_due_date"]) - today()).days


def _days_late(loan) -> int:
    """Days since the oldest missed weekly payment was due."""
    if loan["installments_missed"] == 0:
        return 0
    return 7 * loan["installments_missed"] - _days_until_due(loan)


def _amount_overdue(loan) -> float:
    """Missed payments are owed at the standard price: the discount is lost."""
    return round(loan["installments_missed"] * loan["installment_standard"], 2)


def _total_overdue(loan) -> float:
    return round(_amount_overdue(loan) + loan["late_interest_accrued"], 2)


def _hold_until(conn, loan) -> Optional[str]:
    """The collections hold: while a promise is active and not yet due, the
    bank does not contact the customer about this loan."""
    active = _promises(conn, loan["id"], "active")
    if active and date.fromisoformat(active[0]["promised_date"]) >= today():
        return active[0]["promised_date"]
    return None


def _promise_refusal(conn, loan) -> Optional[str]:
    """Why this customer cannot make a new promise, or None if they can."""
    if loan is None:
        return "This customer has no loan, so there is nothing to promise."
    if _promises(conn, loan["id"], "active"):
        return (
            "The customer already has an active payment promise. A second one cannot "
            "be registered. Remind them of the existing one (see get_loan_status)."
        )
    if len(_promises(conn, loan["id"], "broken")) > config.MAX_BROKEN_PROMISES:
        return (
            "The customer has broken too many promises to make a new one here. "
            "Hand off with reason 'policy_limit'."
        )
    return None


def _offer_refusal(conn, loan) -> Optional[str]:
    """Why the catch-up program is not available, or None if it is."""
    name = config.REGULARIZATION_NAME
    if loan is None:
        return "This customer has no loan."
    missed = loan["installments_missed"]
    if missed < config.REGULARIZATION_MIN_MISSED:
        return (
            f"'{name}' is for loans with at least {config.REGULARIZATION_MIN_MISSED} missed "
            f"weekly payments; this loan has {missed}. The customer can pay what is due "
            "or register a payment promise."
        )
    if missed > config.REGULARIZATION_MAX_MISSED:
        return (
            f"'{name}' is for loans with at most {config.REGULARIZATION_MAX_MISSED} missed "
            f"weekly payments; this loan has {missed}. Hand off with reason 'policy_limit'."
        )
    if loan["has_plan"]:
        return (
            f"'{name}' is not available for a loan that is already restructured, renewed "
            "or on a plan. The customer can still register a payment promise. If they "
            "insist on the program, hand off with reason 'policy_limit'."
        )
    used = conn.execute(
        "SELECT 1 FROM payment_promises WHERE loan_id = ? AND offer_id IS NOT NULL",
        (loan["id"],),
    ).fetchone()
    if used:
        return (
            f"'{name}' was already used on this loan and can be used only once. "
            "Remind the customer of it if it is still active (see get_loan_status); "
            "otherwise they can register a payment promise."
        )
    return _promise_refusal(conn, loan)


def _offer(loan) -> dict:
    missed, on_time = loan["installments_missed"], loan["installment_on_time"]
    # Without the program, by the pay-by date the customer owes everything
    # overdue plus the coming payment, all at the standard price.
    owed = round(_total_overdue(loan) + loan["installment_standard"], 2)
    to_pay = round((missed + 1) * on_time, 2)
    return {
        "offer_id": f"PAC-{loan['id']:04d}-{today():%Y%m%d}",
        "program": config.REGULARIZATION_NAME,
        "amount_owed": owed,
        "amount_waived": round(owed - to_pay, 2),
        "weeks_late": missed,
        "amount_to_pay": to_pay,
        "pay_by_date": (
            today() + timedelta(days=config.REGULARIZATION_PAY_WITHIN_DAYS)).isoformat(),
        "amount_owed_covers": (
            f"the {missed} missed weekly payments and the coming one at the standard "
            "price, plus the late interest: what is due by pay_by_date without the program"
        ),
        "amount_to_pay_covers": (
            f"the same {missed + 1} weekly payments at the on-time price, with no late "
            "interest. Afterwards the loan is up to date, the coming payment included"
        ),
        "condition": "Nothing is waived unless the full amount is paid by pay_by_date.",
        "to_accept": "Call register_payment_promise with this offer_id, amount_to_pay as "
                     "the amount, and a date no later than pay_by_date.",
    }


def _promise_date(text: str, latest: date) -> date:
    try:
        promised = date.fromisoformat(text)
    except ValueError:
        raise ToolError("promised_date must be a real date written as YYYY-MM-DD.")
    if promised < today():
        raise ToolError(f"promised_date is in the past. Today is {today().isoformat()}.")
    if promised > latest:
        raise ToolError(
            f"promised_date is too far away. The latest allowed date is {latest.isoformat()}."
        )
    return promised


def get_loan_status(session) -> dict:
    loan = _loan(session.conn, session.customer_id)
    if loan is None:
        return {"has_loan": False}
    late = loan["installments_missed"] > 0
    active = _promises(session.conn, loan["id"], "active")
    last_payment = session.conn.execute(
        "SELECT amount, paid_on, channel FROM payments WHERE loan_id = ?"
        " ORDER BY paid_on DESC LIMIT 1", (loan["id"],)
    ).fetchone()
    limits = {
        "minimum_amount": loan["installment_on_time"],
        "maximum_amount": _total_overdue(loan) if late else loan["installment_standard"],
        "latest_date": (today() + timedelta(days=config.PROMISE_MAX_DAYS)).isoformat(),
    }
    if not late:
        limits["note"] = (
            "Only for a customer who cannot pay by next_due_date. The date must be after "
            "it, and a payment made after it is at the standard price."
        )
    return {
        "has_loan": True,
        "product": loan["product"],
        "outstanding_balance": loan["outstanding_balance"],
        "installment_on_time": loan["installment_on_time"],
        "installment_standard": loan["installment_standard"],
        "on_time_discount": "lost while the loan is late" if late else "applies",
        "next_due_date": loan["next_due_date"],
        "days_until_due": _days_until_due(loan),
        "installments_missed": loan["installments_missed"],
        "days_late": _days_late(loan),
        "amount_overdue": _amount_overdue(loan),
        "late_interest_accrued": loan["late_interest_accrued"],
        "total_overdue": _total_overdue(loan),
        "last_payment_on_record": dict(last_payment) if last_payment else None,
        "has_plan": bool(loan["has_plan"]),
        "active_promise": (
            {"amount": active[0]["amount"], "promised_date": active[0]["promised_date"],
             "under_program": active[0]["offer_id"] is not None}
            if active else None
        ),
        "hold_until": _hold_until(session.conn, loan),
        "broken_promises": len(_promises(session.conn, loan["id"], "broken")),
        "promise_limits": limits,
    }


def compute_regularization_offer(session) -> dict:
    loan = _loan(session.conn, session.customer_id)
    refusal = _offer_refusal(session.conn, loan)
    if refusal:
        raise ToolError(refusal)
    offer = _offer(loan)
    # Keep a record that the offer was shown. It commits the customer to nothing.
    session.conn.execute(
        "INSERT OR REPLACE INTO regularization_offers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (offer["offer_id"], loan["id"], offer["amount_owed"], offer["amount_waived"],
         offer["weeks_late"], offer["amount_to_pay"], offer["pay_by_date"], today().isoformat()),
    )
    session.conn.commit()
    return offer


def get_payment_options(session) -> dict:
    return {
        "where_to_pay": config.PAYMENT_CHANNELS,
        f"only_when_paying_under_{config.REGULARIZATION_NAME.lower().replace(' ', '_')}":
            config.REGULARIZATION_CASHIER_INSTRUCTION,
    }


def register_payment_promise(session, amount: float, promised_date: str,
                             offer_id: Optional[str] = None) -> dict:
    loan = _loan(session.conn, session.customer_id)
    refusal = _promise_refusal(session.conn, loan)
    if refusal:
        raise ToolError(refusal)
    late = loan["installments_missed"] > 0
    result = {}

    if offer_id:
        refusal = _offer_refusal(session.conn, loan)
        if refusal:
            raise ToolError(refusal)
        offer = _offer(loan)
        if offer_id != offer["offer_id"]:
            raise ToolError(
                "Unknown or expired offer_id. Call compute_regularization_offer again."
            )
        promised = _promise_date(promised_date, date.fromisoformat(offer["pay_by_date"]))
        if abs(amount - offer["amount_to_pay"]) >= 0.01:
            raise ToolError(
                f"A promise under '{config.REGULARIZATION_NAME}' must be for its full "
                f"amount: {offer['amount_to_pay']:.2f} pesos."
            )
        result = {
            "program": config.REGULARIZATION_NAME,
            "amount_waived": offer["amount_waived"],
            "condition": offer["condition"],
            "tell_the_customer": config.REGULARIZATION_CASHIER_INSTRUCTION,
        }
    else:
        promised = _promise_date(promised_date, today() + timedelta(days=config.PROMISE_MAX_DAYS))
        minimum = loan["installment_on_time"]
        if late:
            maximum, maximum_is = _total_overdue(loan), "the total overdue"
        else:
            # Not late yet: the customer is saying they will miss the coming payment.
            if promised <= date.fromisoformat(loan["next_due_date"]):
                raise ToolError(
                    f"No promise is needed: the payment is not due until "
                    f"{loan['next_due_date']}. A promise is only for a later date."
                )
            maximum, maximum_is = loan["installment_standard"], "one weekly payment"
        if amount < minimum:
            raise ToolError(
                f"The amount is too low. The minimum promise is one on-time weekly "
                f"payment: {minimum:.2f} pesos."
            )
        if amount > maximum:
            raise ToolError(
                f"The amount is more than {maximum_is}. The maximum promise is "
                f"{maximum:.2f} pesos."
            )

    promise_id = session.conn.execute(
        "INSERT INTO payment_promises"
        " (loan_id, amount, promised_date, status, created_on, offer_id, amount_waived)"
        " VALUES (?, ?, ?, 'active', ?, ?, ?)",
        (loan["id"], amount, promised.isoformat(), today().isoformat(),
         offer_id or None, result.get("amount_waived", 0)),
    ).lastrowid
    session.conn.commit()
    session.log.record("outcome", outcome="promise_registered", amount=amount,
                       promised_date=promised_date, under_program=bool(offer_id))
    return {
        "registered": True,
        "promise_id": promise_id,
        "amount": amount,
        "promised_date": promised.isoformat(),
        "hold_until": promised.isoformat(),
        "where_to_pay": config.PAYMENT_CHANNELS,
        **result,
    }


def outbound_check(conn, customer_id) -> Optional[str]:
    """Why the bank must not start a payment conversation now, or None."""
    loan = _loan(conn, customer_id)
    if loan is None:
        return "there is no loan, so there is no payment to talk about"
    hold = _hold_until(conn, loan)
    if hold:
        promise = _promises(conn, loan["id"], "active")[0]
        return (
            f"there is an active promise for ${promise['amount']:,.2f} due "
            f"{plain_date(hold)}, and the hold suppresses contact until then"
        )
    if loan["installments_missed"] == 0 and _days_until_due(loan) > config.REMINDER_DAYS_BEFORE_DUE:
        return (
            f"the next payment is not due for {_days_until_due(loan)} days, and reminders "
            f"start {config.REMINDER_DAYS_BEFORE_DUE} days before the due date"
        )
    return None


def outcome(conn, customer_id) -> dict:
    """The customer's promise and catch-up offer, for the outcome summary."""
    summary = {"Promise": "none", "Offer shown": "none"}
    loan = _loan(conn, customer_id)
    if loan is None:
        return summary
    active = _promises(conn, loan["id"], "active")
    if active:
        p = active[0]
        summary["Promise"] = (
            f"${p['amount']:,.2f} on {p['promised_date']}, hold until "
            f"{_hold_until(conn, loan) or 'ended'}"
            + (f", under {config.REGULARIZATION_NAME}" if p["offer_id"] else "")
            + (" (made in this conversation)" if p["created_on"] == today().isoformat()
               else " (made earlier)")
        )
    offer = conn.execute(
        "SELECT * FROM regularization_offers WHERE loan_id = ? ORDER BY shown_on DESC LIMIT 1",
        (loan["id"],),
    ).fetchone()
    if offer:
        accepted = any(p["offer_id"] == offer["offer_id"] for p in active)
        summary["Offer shown"] = (
            f"{config.REGULARIZATION_NAME}: owes ${offer['amount_owed']:,.2f}, waived "
            f"${offer['amount_waived']:,.2f}, pays ${offer['amount_to_pay']:,.2f} by "
            f"{offer['pay_by_date']} ({'accepted' if accepted else 'not accepted'})"
        )
    return summary


TOOLS = [
    Tool(
        name="get_loan_status",
        description=(
            "Get the verified customer's loan: the weekly payment at its on-time and "
            "standard price, when the next one is due, how many are missed, late "
            "interest, the last payment on record, whether the loan is on a plan, any "
            "active payment promise and the collections hold that goes with it, how "
            "many promises were broken, and the limits a new promise must respect."
        ),
        handler=get_loan_status,
    ),
    Tool(
        name="compute_regularization_offer",
        description=(
            f"Work out the '{config.REGULARIZATION_NAME}' catch-up offer for the verified "
            "customer: the amount owed, the amount waived, the weeks late, the amount to "
            "pay and the pay-by date. It refuses, with the reason, if the loan does not "
            "qualify. It commits the customer to nothing."
        ),
        handler=compute_regularization_offer,
    ),
    Tool(
        name="get_payment_options",
        description=(
            "Get where a loan can be paid. Works without verification: it contains "
            "nothing about any customer."
        ),
        handler=get_payment_options,
        requires_verification=False,
    ),
    Tool(
        name="register_payment_promise",
        description=(
            "Record the customer's commitment to pay a given amount on a given date. "
            "Call it only after the customer has clearly agreed to both. To accept a "
            f"'{config.REGULARIZATION_NAME}' offer, also pass its offer_id; the amount "
            "must then be the offer's amount_to_pay."
        ),
        handler=register_payment_promise,
        properties={
            "amount": {"type": "number", "description": "Pesos"},
            "promised_date": {"type": "string", "description": "YYYY-MM-DD"},
            "offer_id": {
                "type": "string",
                "description": "From compute_regularization_offer. Leave out for an "
                               "ordinary promise.",
            },
        },
        required=["amount", "promised_date"],
    ),
]

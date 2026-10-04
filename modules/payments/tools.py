"""Payment assistant tools. Every policy number comes from config.py and is
enforced here, whatever the rulebook or the customer says.

A "commitment" is a row in payment_promises: either a plain payment promise
or an accepted catch-up offer (kind = 'regularization').
"""

from datetime import date, timedelta
from typing import Optional

import config
from core.clock import today
from core.tools import Tool, ToolError


def _loan(conn, customer_id):
    return conn.execute("SELECT * FROM loans WHERE customer_id = ?", (customer_id,)).fetchone()


def _commitments(conn, loan_id, status):
    return conn.execute(
        "SELECT * FROM payment_promises WHERE loan_id = ? AND status = ? ORDER BY promised_date",
        (loan_id, status),
    ).fetchall()


def _days_late(loan) -> int:
    return max((today() - date.fromisoformat(loan["next_due_date"])).days, 0)


def _late_interest(loan) -> float:
    return round(
        loan["amount_overdue"] * config.LATE_INTEREST_DAILY_PERCENT / 100 * _days_late(loan), 2
    )


def _total_overdue(loan) -> float:
    return round(loan["amount_overdue"] + _late_interest(loan), 2)


def _minimum_promise(loan) -> float:
    """One weekly payment, or everything overdue if that is less."""
    return min(loan["weekly_payment"], _total_overdue(loan))


def _hold_until(conn, loan) -> Optional[str]:
    """The collections hold: while a commitment is active and not yet due,
    the bank does not contact the customer about this loan."""
    active = _commitments(conn, loan["id"], "active")
    if active and date.fromisoformat(active[0]["promised_date"]) >= today():
        return active[0]["promised_date"]
    return None


def _commitment_refusal(conn, loan) -> Optional[str]:
    """Why this customer cannot make any new commitment, or None if they can."""
    if loan is None or loan["amount_overdue"] <= 0:
        return "This customer has no overdue amount, so no payment commitment is needed."
    if _commitments(conn, loan["id"], "active"):
        return (
            "The customer already has an active payment commitment. A second one cannot "
            "be registered. Remind them of the existing one (see get_loan_status)."
        )
    if len(_commitments(conn, loan["id"], "broken")) > config.MAX_BROKEN_PROMISES:
        return (
            "The customer has broken too many promises to make a new commitment here. "
            "Hand off with reason 'policy_limit'."
        )
    return None


def _regularization_refusal(conn, loan) -> Optional[str]:
    """Why the catch-up offer is not available, or None if it is."""
    refusal = _commitment_refusal(conn, loan)
    if refusal:
        return refusal
    days_late = _days_late(loan)
    if days_late < config.REGULARIZATION_MIN_DAYS_LATE:
        return (
            f"'{config.REGULARIZATION_NAME}' is offered from "
            f"{config.REGULARIZATION_MIN_DAYS_LATE} days late; this loan is {days_late} "
            "days late. The customer can pay what is overdue or register a promise."
        )
    if days_late > config.REGULARIZATION_MAX_DAYS_LATE:
        return (
            f"'{config.REGULARIZATION_NAME}' is not available after "
            f"{config.REGULARIZATION_MAX_DAYS_LATE} days late. Hand off with reason "
            "'policy_limit'."
        )
    used = conn.execute(
        "SELECT 1 FROM payment_promises WHERE loan_id = ? AND kind = 'regularization'",
        (loan["id"],),
    ).fetchone()
    if used:
        return (
            f"'{config.REGULARIZATION_NAME}' was already used on this loan and can be "
            "used only once. The customer can still register a promise."
        )
    return None


def _regularization_terms(loan) -> dict:
    waived = round(_late_interest(loan) * config.REGULARIZATION_WAIVER_PERCENT / 100, 2)
    return {
        "name": config.REGULARIZATION_NAME,
        "amount_to_pay": round(_total_overdue(loan) - waived, 2),
        "late_interest_waived": waived,
        "latest_pay_by_date": (
            today() + timedelta(days=config.REGULARIZATION_MAX_DAYS)).isoformat(),
        "condition": "The waiver applies only if the whole amount is paid by the agreed "
                     "date. Otherwise the full late interest is owed.",
    }


def _commitment_date(text: str, field: str, max_days: int) -> date:
    try:
        chosen = date.fromisoformat(text)
    except ValueError:
        raise ToolError(f"{field} must be a real date written as YYYY-MM-DD.")
    latest = today() + timedelta(days=max_days)
    if chosen < today():
        raise ToolError(f"{field} is in the past. Today is {today().isoformat()}.")
    if chosen > latest:
        raise ToolError(
            f"{field} is too far away. The latest allowed date is {latest.isoformat()}."
        )
    return chosen


def _register(session, loan, kind: str, amount: float, promised: date, waived: float) -> dict:
    commitment_id = session.conn.execute(
        "INSERT INTO payment_promises"
        " (loan_id, kind, amount, interest_waived, promised_date, status, created_on)"
        " VALUES (?, ?, ?, ?, ?, 'active', ?)",
        (loan["id"], kind, amount, waived, promised.isoformat(), today().isoformat()),
    ).lastrowid
    session.conn.commit()
    return {
        "registered": True,
        "commitment_id": commitment_id,
        "amount": amount,
        "pay_by_date": promised.isoformat(),
        "collections_hold_until": promised.isoformat(),
        "where_to_pay": config.PAYMENT_CHANNELS,
    }


def get_loan_status(session) -> dict:
    loan = _loan(session.conn, session.customer_id)
    if loan is None:
        return {"has_loan": False}
    active = _commitments(session.conn, loan["id"], "active")
    overdue = loan["amount_overdue"] > 0
    return {
        "has_loan": True,
        "product": loan["product"],
        "outstanding_balance": loan["outstanding_balance"],
        "weekly_payment": loan["weekly_payment"],
        "next_due_date": loan["next_due_date"],
        "days_until_due": max((date.fromisoformat(loan["next_due_date"]) - today()).days, 0),
        "days_late": _days_late(loan),
        "amount_overdue": loan["amount_overdue"],
        "late_interest": _late_interest(loan),
        "total_overdue": _total_overdue(loan),
        "active_commitment": (
            {"kind": active[0]["kind"], "amount": active[0]["amount"],
             "pay_by_date": active[0]["promised_date"]}
            if active else None
        ),
        "collections_hold_until": _hold_until(session.conn, loan),
        "broken_promises": len(_commitments(session.conn, loan["id"], "broken")),
        "promise_limits": (
            {"minimum_amount": _minimum_promise(loan),
             "maximum_amount": _total_overdue(loan),
             "latest_date": (today() + timedelta(days=config.PROMISE_MAX_DAYS)).isoformat()}
            if overdue else None
        ),
    }


def get_payment_options(session) -> dict:
    options = {"where_to_pay": config.PAYMENT_CHANNELS}
    if not session.verified:
        # Where to pay is public information; what this customer owes is not.
        options["amounts"] = None
        options["note"] = "Amounts are available only after verify_identity succeeds."
        return options
    loan = _loan(session.conn, session.customer_id)
    if loan is None:
        options["amounts"] = None
        options["note"] = "This customer has no loan."
    elif loan["amount_overdue"] <= 0:
        options["amounts"] = {
            "next_payment": {"amount": loan["weekly_payment"], "due_date": loan["next_due_date"]},
        }
    else:
        refusal = _regularization_refusal(session.conn, loan)
        options["amounts"] = {
            "to_be_up_to_date": _total_overdue(loan),
            "catch_up_offer": (
                {"available": False, "reason": refusal} if refusal
                else {"available": True, **_regularization_terms(loan)}
            ),
        }
    return options


def register_payment_promise(session, amount: float, promised_date: str) -> dict:
    loan = _loan(session.conn, session.customer_id)
    refusal = _commitment_refusal(session.conn, loan)
    if refusal:
        raise ToolError(refusal)
    promised = _commitment_date(promised_date, "promised_date", config.PROMISE_MAX_DAYS)
    minimum, maximum = _minimum_promise(loan), _total_overdue(loan)
    if amount < minimum:
        raise ToolError(
            f"The amount is too low. The minimum promise is one weekly payment: "
            f"{minimum:.2f} pesos."
        )
    if amount > maximum:
        raise ToolError(
            f"The amount is more than the total overdue. The maximum promise is "
            f"{maximum:.2f} pesos."
        )
    result = _register(session, loan, "promise", amount, promised, waived=0)
    session.log.record("outcome", outcome="promise_registered",
                       amount=amount, promised_date=promised_date)
    return result


def accept_regularization_offer(session, pay_by_date: str) -> dict:
    loan = _loan(session.conn, session.customer_id)
    refusal = _regularization_refusal(session.conn, loan)
    if refusal:
        raise ToolError(refusal)
    pay_by = _commitment_date(pay_by_date, "pay_by_date", config.REGULARIZATION_MAX_DAYS)
    terms = _regularization_terms(loan)
    result = _register(session, loan, "regularization", terms["amount_to_pay"], pay_by,
                       waived=terms["late_interest_waived"])
    result["late_interest_waived"] = terms["late_interest_waived"]
    result["condition"] = terms["condition"]
    session.log.record("outcome", outcome="regularization_accepted",
                       amount=terms["amount_to_pay"], pay_by_date=pay_by_date,
                       late_interest_waived=terms["late_interest_waived"])
    return result


def outbound_check(conn, customer_id) -> Optional[str]:
    """Why the bank must not start a payment conversation now, or None."""
    loan = _loan(conn, customer_id)
    if loan is None:
        return "This customer has no loan, so there is no payment to talk about."
    hold = _hold_until(conn, loan)
    if hold:
        return (
            f"Collections hold: the customer has committed to pay by {hold}. The bank "
            "does not contact them about this loan until then."
        )
    if loan["amount_overdue"] <= 0:
        days_until_due = (date.fromisoformat(loan["next_due_date"]) - today()).days
        if days_until_due > config.REMINDER_DAYS_BEFORE_DUE:
            return (
                f"The next payment is due in {days_until_due} days. Reminders start "
                f"{config.REMINDER_DAYS_BEFORE_DUE} days before the due date."
            )
    return None


TOOLS = [
    Tool(
        name="get_loan_status",
        description=(
            "Get the verified customer's loan: balance, weekly payment, when the next "
            "payment is due or how late it is, late interest, any active payment "
            "commitment and the collections hold that goes with it, how many promises "
            "were broken, and the limits a new promise must respect."
        ),
        handler=get_loan_status,
    ),
    Tool(
        name="get_payment_options",
        description=(
            "Get where and how a loan can be paid. Before verification it returns only "
            "that. For a verified customer it also returns what they can pay: the next "
            f"payment, or the total overdue and the '{config.REGULARIZATION_NAME}' "
            "catch-up offer if they qualify."
        ),
        handler=get_payment_options,
        requires_verification=False,
    ),
    Tool(
        name="register_payment_promise",
        description=(
            "Record the customer's commitment to pay a given amount on a given date. "
            "Call it only after the customer has clearly agreed to both."
        ),
        handler=register_payment_promise,
        properties={
            "amount": {"type": "number", "description": "Pesos"},
            "promised_date": {"type": "string", "description": "YYYY-MM-DD"},
        },
        required=["amount", "promised_date"],
    ),
    Tool(
        name="accept_regularization_offer",
        description=(
            f"Record that the customer accepts the '{config.REGULARIZATION_NAME}' "
            "catch-up offer returned by get_payment_options and will pay its full "
            "amount by a given date. Call it only after the customer has clearly "
            "agreed to the amount and the date."
        ),
        handler=accept_regularization_offer,
        properties={"pay_by_date": {"type": "string", "description": "YYYY-MM-DD"}},
        required=["pay_by_date"],
    ),
]

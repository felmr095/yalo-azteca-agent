"""Collections tools. Every policy number comes from config.py and is
enforced here, whatever the rulebook or the customer says."""

from datetime import date, timedelta

import config
from core.clock import today
from core.tools import Tool, ToolError


def _loan(session):
    return session.conn.execute(
        "SELECT * FROM loans WHERE customer_id = ?", (session.customer_id,)
    ).fetchone()


def _promises(session, loan_id, status):
    return session.conn.execute(
        "SELECT * FROM payment_promises WHERE loan_id = ? AND status = ? ORDER BY promised_date",
        (loan_id, status),
    ).fetchall()


def _minimum_promise(loan) -> float:
    return round(loan["amount_overdue"] * config.PROMISE_MIN_PERCENT / 100, 2)


def get_loan_status(session) -> dict:
    loan = _loan(session)
    if loan is None:
        return {"has_loan": False}
    days_late = max((today() - date.fromisoformat(loan["next_due_date"])).days, 0)
    active = _promises(session, loan["id"], "active")
    return {
        "has_loan": True,
        "product": loan["product"],
        "outstanding_balance": loan["outstanding_balance"],
        "weekly_payment": loan["weekly_payment"],
        "next_due_date": loan["next_due_date"],
        "days_late": days_late,
        "amount_overdue": loan["amount_overdue"],
        "active_promise": (
            {"amount": active[0]["amount"], "promised_date": active[0]["promised_date"]}
            if active else None
        ),
        "broken_promises": len(_promises(session, loan["id"], "broken")),
        "minimum_promise_amount": _minimum_promise(loan),
        "latest_promise_date": (today() + timedelta(days=config.PROMISE_MAX_DAYS)).isoformat(),
    }


def register_payment_promise(session, amount: float, promised_date: str) -> dict:
    loan = _loan(session)
    if loan is None or loan["amount_overdue"] <= 0:
        raise ToolError("This customer has no overdue amount, so no promise is needed.")
    if _promises(session, loan["id"], "active"):
        raise ToolError(
            "The customer already has an active payment promise. A second one cannot "
            "be registered. Remind them of the existing one (see get_loan_status)."
        )
    if len(_promises(session, loan["id"], "broken")) > config.MAX_BROKEN_PROMISES:
        raise ToolError(
            "The customer has broken too many promises to register a new one here. "
            "Hand off with reason 'policy_limit'."
        )
    try:
        promised = date.fromisoformat(promised_date)
    except ValueError:
        raise ToolError("promised_date must be a real date written as YYYY-MM-DD.")
    latest = today() + timedelta(days=config.PROMISE_MAX_DAYS)
    if promised < today():
        raise ToolError(f"promised_date is in the past. Today is {today().isoformat()}.")
    if promised > latest:
        raise ToolError(
            f"promised_date is too far away. The latest allowed date is {latest.isoformat()}."
        )
    minimum = _minimum_promise(loan)
    if amount < minimum:
        raise ToolError(f"The amount is too low. The minimum promise is {minimum:.2f} pesos.")
    if amount > loan["outstanding_balance"]:
        raise ToolError(
            f"The amount is more than the whole loan balance "
            f"({loan['outstanding_balance']:.2f} pesos)."
        )

    promise_id = session.conn.execute(
        "INSERT INTO payment_promises (loan_id, amount, promised_date, status, created_on)"
        " VALUES (?, ?, ?, 'active', ?)",
        (loan["id"], amount, promised_date, today().isoformat()),
    ).lastrowid
    session.conn.commit()
    session.log.record("outcome", outcome="promise_registered",
                       amount=amount, promised_date=promised_date)
    return {"registered": True, "promise_id": promise_id, "amount": amount,
            "promised_date": promised_date, "where_to_pay": config.PAYMENT_CHANNELS}


def update_contact_phone(session, new_phone: str) -> dict:
    digits = "".join(ch for ch in new_phone if ch.isdigit())
    if len(digits) == 12 and digits.startswith("52"):
        digits = digits[2:]
    if len(digits) != 10:
        raise ToolError("new_phone must be a 10-digit Mexican number.")
    formatted = f"+52 {digits}"
    taken = session.conn.execute(
        "SELECT 1 FROM customers WHERE REPLACE(phone, ' ', '') = ? AND id != ?",
        (formatted.replace(" ", ""), session.customer_id),
    ).fetchone()
    if taken:
        raise ToolError(
            "This number cannot be registered here. Hand off with reason 'other'. "
            "Do not tell the customer why."
        )
    session.conn.execute(
        "UPDATE customers SET phone = ? WHERE id = ?", (formatted, session.customer_id)
    )
    session.conn.commit()
    session.log.record("outcome", outcome="phone_updated")
    return {"updated": True, "new_phone": formatted}


TOOLS = [
    Tool(
        name="get_loan_status",
        description=(
            "Get the verified customer's loan: balance, weekly payment, how late it "
            "is, any active payment promise, how many promises were broken, and the "
            "limits a new promise must respect."
        ),
        handler=get_loan_status,
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
        name="update_contact_phone",
        description="Change the phone number the bank uses to contact the verified customer.",
        handler=update_contact_phone,
        properties={"new_phone": {"type": "string", "description": "10-digit Mexican number"}},
        required=["new_phone"],
    ),
]

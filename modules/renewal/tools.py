"""Renewal tools. Every policy number comes from config.py and is enforced
here, whatever the rulebook or the customer says.

The rule that comes before all others: a customer who is late or has an
active payment promise is never offered credit. Every tool that offers,
quotes or starts a loan checks it.
"""

from datetime import date, timedelta
from typing import Optional

import config
from core.clock import today
from core.tools import Tool, ToolError

NO_CREDIT = (
    "Do not offer, quote or discuss a new loan. If the customer needs help with "
    "their payments, help them with the payment tools instead."
)
NO_OFFER = (
    "Tell the customer there is no offer for them at the moment. Do not list the "
    "bank's internal criteria."
)


def _loan(conn, customer_id):
    return conn.execute("SELECT * FROM loans WHERE customer_id = ?", (customer_id,)).fetchone()


def _promises(conn, loan_id):
    """Payment promises on the loan, if the payment assistant is switched on."""
    table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'payment_promises'"
    ).fetchone()
    if not table:
        return []
    return conn.execute(
        "SELECT status, created_on FROM payment_promises WHERE loan_id = ?", (loan_id,)
    ).fetchall()


def _days_ago(days: int) -> str:
    return (today() - timedelta(days=days)).isoformat()


def _recent_offer(conn, customer_id):
    """The latest decline or application still inside the waiting period, as
    a row with what the customer did and the day, or None."""
    row = conn.execute(
        "SELECT 'declined an offer' AS what, declined_on AS day FROM renewal_declines"
        " WHERE customer_id = :c UNION ALL"
        " SELECT 'started an application', created_on FROM loan_applications"
        " WHERE customer_id = :c ORDER BY day DESC LIMIT 1",
        {"c": customer_id},
    ).fetchone()
    return row if row and row["day"] > _days_ago(config.RENEWAL_REOFFER_DAYS) else None


def _no_offer_before(conn, customer_id) -> Optional[str]:
    """If the customer declined or applied recently: the date offers may resume."""
    recent = _recent_offer(conn, customer_id)
    if recent is None:
        return None
    return (date.fromisoformat(recent["day"])
            + timedelta(days=config.RENEWAL_REOFFER_DAYS)).isoformat()


def _assess(conn, customer_id) -> dict:
    """Everything the eligibility decision rests on, and the decision."""
    loan = _loan(conn, customer_id)
    if loan is None:
        return {"eligible": False, "why_not": ["The customer has no loan to renew."],
                "instruction": NO_OFFER}

    promises = _promises(conn, loan["id"])
    late_now = loan["installments_missed"] > 0
    active_promise = any(p["status"] == "active" for p in promises)
    promise_since = _days_ago(30 * config.RENEWAL_NO_PROMISE_MONTHS)
    recent_promise = any(p["created_on"] >= promise_since for p in promises)

    why_not = []
    if late_now:
        why_not.append("The loan has missed payments.")
    if active_promise:
        why_not.append("The customer has an active payment promise.")
    elif recent_promise:
        why_not.append(
            f"A payment promise in the last {config.RENEWAL_NO_PROMISE_MONTHS} months.")
    facts = {"promise_in_last_months": recent_promise}

    profile = conn.execute(
        "SELECT * FROM renewal_profiles WHERE loan_id = ?", (loan["id"],)).fetchone()
    if profile is None:
        why_not.append("No pre-approved offer on record.")
    else:
        paid = profile["installments_paid"]
        on_time = round(100 * profile["installments_on_time"] / paid, 1) if paid else 0
        repaid = round(100 * paid / profile["term_weeks"], 1)
        last_late = profile["last_late_payment_on"]
        late_recently = bool(last_late and last_late > _days_ago(7 * config.RENEWAL_NO_LATE_WEEKS))
        if on_time < config.RENEWAL_MIN_ON_TIME_PERCENT:
            why_not.append(f"Paid on time {on_time}% of the time; "
                           f"{config.RENEWAL_MIN_ON_TIME_PERCENT}% is needed.")
        if late_recently:
            why_not.append(f"A late payment in the last {config.RENEWAL_NO_LATE_WEEKS} weeks.")
        if repaid < config.RENEWAL_MIN_REPAID_PERCENT:
            why_not.append(f"{repaid}% of the loan repaid; "
                           f"{config.RENEWAL_MIN_REPAID_PERCENT}% is needed.")
        if profile["preapproved_max"] < config.RENEWAL_MIN_AMOUNT:
            why_not.append("The pre-approved limit is below the smallest loan.")
        facts.update({
            "on_time_percent": on_time,
            "late_payment_in_last_weeks": late_recently,
            "share_repaid_percent": repaid,
        })

    result = {"eligible": not why_not, "why_not": why_not, **facts}
    if why_not:
        result["instruction"] = NO_CREDIT if (late_now or active_promise) else NO_OFFER
    else:
        result.update({
            "preapproved_max": profile["preapproved_max"],
            "minimum_amount": config.RENEWAL_MIN_AMOUNT,
            "terms_weeks": config.RENEWAL_TERMS_WEEKS,
        })
    return result


def _require_eligible(session) -> dict:
    found = _assess(session.conn, session.customer_id)
    if not found["eligible"]:
        raise ToolError(f"This customer cannot be offered a loan: {' '.join(found['why_not'])} "
                        f"{found['instruction']}")
    return found


def _check_amount_and_term(found: dict, amount: float, term_weeks: int) -> None:
    if term_weeks not in config.RENEWAL_TERMS_WEEKS:
        raise ToolError(f"term_weeks must be one of {config.RENEWAL_TERMS_WEEKS}.")
    if amount < config.RENEWAL_MIN_AMOUNT:
        raise ToolError(f"The smallest loan is {config.RENEWAL_MIN_AMOUNT:.2f} pesos.")
    if amount > found["preapproved_max"]:
        raise ToolError(
            f"The amount is above this customer's pre-approved limit of "
            f"{found['preapproved_max']:.2f} pesos. Explain the limit and offer an amount "
            "within it. If they insist on more, hand off with reason 'policy_limit'."
        )


def _weekly_payment(amount: float, term_weeks: int, annual_rate_percent: float) -> float:
    """Equal weekly payments at the annual rate, without IVA. An estimate:
    the real figure would come from the bank's own system."""
    weekly_rate = annual_rate_percent / 100 / 52
    return round(amount * weekly_rate / (1 - (1 + weekly_rate) ** -term_weeks), 2)


def get_renewal_eligibility(session) -> dict:
    found = _assess(session.conn, session.customer_id)
    no_offer_before = _no_offer_before(session.conn, session.customer_id)
    if no_offer_before:
        found["recently_declined_or_applied"] = (
            f"Do not bring up the offer yourself before {no_offer_before}. "
            "Answer only if the customer asks about a new loan."
        )
    return found


def quote_loan(session, amount: float, term_weeks: int) -> dict:
    found = _require_eligible(session)
    _check_amount_and_term(found, amount, term_weeks)
    rates = config.PUBLISHED_RATES[config.RENEWAL_PRODUCT]
    weekly = _weekly_payment(amount, term_weeks, rates["annual_rate"])
    total = round(weekly * term_weeks, 2)
    session.conn.execute(
        "INSERT INTO loan_quotes (customer_id, amount, term_weeks, weekly_payment,"
        " total_to_pay, created_on) VALUES (?, ?, ?, ?, ?, ?)",
        (session.customer_id, amount, term_weeks, weekly, total, today().isoformat()),
    )
    session.conn.commit()
    return {
        "product": config.RENEWAL_PRODUCT,
        "amount": amount,
        "term_weeks": term_weeks,
        "weekly_payment": weekly,
        "total_to_pay": total,
        "total_interest": round(total - amount, 2),
        "annual_interest_rate_percent": rates["annual_rate"],
        "cat_percent": rates["cat"],
        "tell_the_customer": (
            "The weekly payment, the total to pay and the CAT, said as "
            f"'CAT promedio {rates['cat']}% sin IVA, informativo'. This is an estimate; "
            "the final terms are shown in the app before they confirm."
        ),
    }


def start_loan_application(session, amount: float, term_weeks: int) -> dict:
    found = _require_eligible(session)
    _check_amount_and_term(found, amount, term_weeks)
    existing = session.conn.execute(
        "SELECT reference, created_on FROM loan_applications WHERE customer_id = ?"
        " AND created_on > ?", (session.customer_id, _days_ago(config.RENEWAL_REOFFER_DAYS)),
    ).fetchone()
    if existing:
        raise ToolError(
            f"An application was already started on {existing['created_on']} (reference "
            f"{existing['reference']}). Remind the customer to confirm it in the app."
        )
    quote = session.conn.execute(
        "SELECT * FROM loan_quotes WHERE customer_id = ? AND amount = ? AND term_weeks = ?"
        " ORDER BY id DESC LIMIT 1", (session.customer_id, amount, term_weeks),
    ).fetchone()
    if quote is None:
        raise ToolError(
            "This amount and term have not been quoted. Call quote_loan first and tell "
            "the customer the weekly payment, the total to pay and the CAT before "
            "starting an application."
        )
    cursor = session.conn.execute(
        "INSERT INTO loan_applications (customer_id, reference, amount, term_weeks,"
        " weekly_payment, total_to_pay, status, created_on) VALUES (?, '', ?, ?, ?, ?, ?, ?)",
        (session.customer_id, amount, term_weeks, quote["weekly_payment"],
         quote["total_to_pay"], config.RENEWAL_APPLICATION_STATUS, today().isoformat()),
    )
    reference = f"SOL-{today():%y%m%d}-{cursor.lastrowid:04d}"
    session.conn.execute("UPDATE loan_applications SET reference = ? WHERE id = ?",
                         (reference, cursor.lastrowid))
    session.conn.commit()
    session.log.record("outcome", outcome="application_started", amount=amount,
                       term_weeks=term_weeks, reference=reference)
    return {
        "reference": reference,
        "status": config.RENEWAL_APPLICATION_STATUS,
        "next_step": (
            "Give the customer the reference and tell them to open the Banco Azteca app "
            "to review and confirm the application. No money is paid out through this "
            "chat, and there is no loan until they confirm in the app."
        ),
    }


def record_offer_decline(session) -> dict:
    if _loan(session.conn, session.customer_id) is None:
        raise ToolError("This customer has no loan, so there is no offer to decline.")
    session.conn.execute(
        "INSERT INTO renewal_declines (customer_id, declined_on) VALUES (?, ?)",
        (session.customer_id, today().isoformat()),
    )
    session.conn.commit()
    session.log.record("outcome", outcome="offer_declined")
    return {"recorded": True,
            "no_new_offer_before": _no_offer_before(session.conn, session.customer_id)}


def outbound_check(conn, customer_id) -> Optional[str]:
    """Why the bank must not offer this customer a loan now, or None."""
    found = _assess(conn, customer_id)
    if not found["eligible"]:
        return ("no loan may be offered. " + " ".join(found["why_not"])).rstrip(".")
    recent = _recent_offer(conn, customer_id)
    if recent:
        since = (today() - date.fromisoformat(recent["day"])).days
        return (
            f"the customer {recent['what']} {since} days ago; no new offer for "
            f"{config.RENEWAL_REOFFER_DAYS - since} more days"
        )
    return None


def outcome(conn, customer_id) -> dict:
    """The customer's quote, application and decline, for the outcome summary."""
    summary = {"Loan quoted": "none", "Loan application": "none", "Loan offer declined": "no"}
    quote = conn.execute(
        "SELECT * FROM loan_quotes WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
        (customer_id,)).fetchone()
    if quote:
        summary["Loan quoted"] = (
            f"${quote['amount']:,.2f} over {quote['term_weeks']} weeks: "
            f"${quote['weekly_payment']:,.2f} a week, ${quote['total_to_pay']:,.2f} in total"
        )
    application = conn.execute(
        "SELECT * FROM loan_applications WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
        (customer_id,)).fetchone()
    if application:
        summary["Loan application"] = (
            f"{application['reference']}: ${application['amount']:,.2f} over "
            f"{application['term_weeks']} weeks, {application['status']}"
        )
    declined = conn.execute(
        "SELECT declined_on FROM renewal_declines WHERE customer_id = ?"
        " ORDER BY declined_on DESC LIMIT 1", (customer_id,)).fetchone()
    if declined:
        summary["Loan offer declined"] = (
            f"yes, on {declined['declined_on']}; no new offer before "
            f"{_no_offer_before(conn, customer_id) or 'now'}"
        )
    return summary


AMOUNT_AND_TERM = {
    "amount": {"type": "number", "description": "Pesos"},
    "term_weeks": {"type": "integer", "description": "Number of weekly payments"},
}

TOOLS = [
    Tool(
        name="get_renewal_eligibility",
        description=(
            "Check whether the verified customer may be offered a new loan: their "
            "on-time payment record, recent late payments, recent payment promises, "
            "how much of the current loan is repaid and, if they qualify, the "
            "pre-approved limit and the terms on offer."
        ),
        handler=get_renewal_eligibility,
    ),
    Tool(
        name="quote_loan",
        description=(
            "Work out the weekly payment, the total to pay and the CAT of a new loan "
            "for the verified customer, for an amount and a term within their limits."
        ),
        handler=quote_loan,
        properties=AMOUNT_AND_TERM,
        required=["amount", "term_weeks"],
    ),
    Tool(
        name="start_loan_application",
        description=(
            "Start the application for a loan that has been quoted in this "
            "conversation. Call it only after the customer has been told the weekly "
            "payment, the total to pay and the CAT, and has clearly said yes. It pays "
            "out nothing: the customer confirms in the app."
        ),
        handler=start_loan_application,
        properties=AMOUNT_AND_TERM,
        required=["amount", "term_weeks"],
    ),
    Tool(
        name="record_offer_decline",
        description=(
            "Record that the verified customer does not want the loan offer, so the "
            "bank does not offer it again for a while."
        ),
        handler=record_offer_decline,
    ),
]

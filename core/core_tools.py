"""Tools every use case shares: verify identity, see the customer's
products, and hand off to a person."""

from datetime import date, datetime

import config
from core.tools import Tool, ToolError

HANDOFF_REASONS = [
    "customer_request",
    "verification_failed",
    "dispute_or_fraud",
    "hardship",
    "policy_limit",
    "third_party",
    "other",
]


def verify_identity(session, date_of_birth: str, account_last4: str) -> dict:
    if session.verified:
        return {"verified": True, "note": "Already verified in this conversation."}
    if session.failed_attempts >= config.MAX_VERIFICATION_ATTEMPTS:
        raise ToolError(
            "Verification is locked: too many failed attempts. Do not ask again. "
            "Hand off with reason 'verification_failed'."
        )
    try:
        date.fromisoformat(date_of_birth)
    except ValueError:
        raise ToolError("date_of_birth must be a real date written as YYYY-MM-DD.")
    if not (len(account_last4) == 4 and account_last4.isdigit()):
        raise ToolError("account_last4 must be exactly 4 digits.")

    customer = session.conn.execute(
        "SELECT full_name, date_of_birth FROM customers WHERE id = ?", (session.customer_id,)
    ).fetchone()
    accounts = session.conn.execute(
        "SELECT number FROM accounts WHERE customer_id = ?", (session.customer_id,)
    ).fetchall()
    matches = (
        customer is not None
        and customer["date_of_birth"] == date_of_birth
        and any(a["number"].endswith(account_last4) for a in accounts)
    )
    if not matches:
        session.failed_attempts += 1
        remaining = config.MAX_VERIFICATION_ATTEMPTS - session.failed_attempts
        if remaining <= 0:
            raise ToolError(
                "Verification failed and no attempts remain. Do not ask again. "
                "Hand off with reason 'verification_failed'."
            )
        raise ToolError(
            f"Verification failed. Attempts remaining: {remaining}. "
            "Do not say which detail was wrong."
        )

    session.verified = True
    return {"verified": True, "customer_name": customer["full_name"]}


def get_customer_profile(session) -> dict:
    customer = session.conn.execute(
        "SELECT full_name FROM customers WHERE id = ?", (session.customer_id,)
    ).fetchone()
    accounts = session.conn.execute(
        "SELECT product, number, balance FROM accounts WHERE customer_id = ?",
        (session.customer_id,),
    ).fetchall()
    loans = session.conn.execute(
        "SELECT product FROM loans WHERE customer_id = ?", (session.customer_id,)
    ).fetchall()
    return {
        "customer_name": customer["full_name"],
        "accounts": [
            {"product": a["product"], "number_last4": a["number"][-4:], "balance": a["balance"]}
            for a in accounts
        ],
        "loans": [l["product"] for l in loans],
    }


def handoff_to_human(session, reason: str, summary: str) -> dict:
    if reason not in HANDOFF_REASONS:
        raise ToolError(f"reason must be one of {HANDOFF_REASONS}.")
    if not summary.strip():
        raise ToolError("summary must not be empty.")
    ticket_id = session.conn.execute(
        "INSERT INTO handoff_tickets (customer_id, phone, verified, reason, summary, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session.customer_id, session.phone, int(session.verified), reason, summary,
         datetime.now().isoformat(timespec="seconds")),
    ).lastrowid
    session.conn.commit()
    session.handed_off = True
    session.log.record("outcome", outcome="handoff", reason=reason, ticket_id=ticket_id)
    if reason == "third_party":
        next_step = ("Apologise for the interruption and say goodbye. Do not say why the "
                     "bank wrote or that anyone will follow up.")
    else:
        next_step = ("Tell the customer a human agent will continue the conversation. "
                     "Do not promise a specific waiting time.")
    return {"ticket_id": f"HT-{ticket_id:04d}", "next_step": next_step}


CORE_TOOLS = [
    Tool(
        name="verify_identity",
        description=(
            "Check the identity of the person in this chat. Call it once you have "
            "both their date of birth and the last 4 digits of their account number. "
            "Must succeed before any tool that reads or changes customer data."
        ),
        handler=verify_identity,
        properties={
            "date_of_birth": {"type": "string", "description": "YYYY-MM-DD"},
            "account_last4": {"type": "string", "description": "Exactly 4 digits"},
        },
        required=["date_of_birth", "account_last4"],
        requires_verification=False,
    ),
    Tool(
        name="get_customer_profile",
        description=(
            "Get the verified customer's name, their accounts with balances, and "
            "which loan products they hold."
        ),
        handler=get_customer_profile,
    ),
    Tool(
        name="handoff_to_human",
        description=(
            "Transfer this conversation to a human agent by creating a ticket. "
            "After it succeeds you can take no further actions in this conversation."
        ),
        handler=handoff_to_human,
        properties={
            "reason": {"type": "string", "enum": HANDOFF_REASONS},
            "summary": {
                "type": "string",
                "description": "In Spanish, for the human agent: what the customer "
                               "needs and what has been done so far.",
            },
        },
        required=["reason", "summary"],
        requires_verification=False,
    ),
]

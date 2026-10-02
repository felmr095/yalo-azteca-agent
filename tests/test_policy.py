"""Policy tests: call the tools directly, with no model involved.

These prove the rules hold in code regardless of what the rulebook says.
They are instant, free and give the same answer every time.

Run with: python -m tests.test_policy
"""

import sys
import tempfile
import traceback

import config
from core.core_tools import CORE_TOOLS
from core.logger import ConversationLog
from core.session import start_session
from core.tools import ToolRegistry
from data import seed

MARIA = {"phone": "+52 55 5550 0101", "date_of_birth": "1988-03-14", "account_last4": "1234"}
JOSE = {"phone": "+52 81 5550 0102", "date_of_birth": "1979-11-02", "account_last4": "2345"}


def new_session(phone=MARIA["phone"]):
    """A fresh database, session and registry, with no model attached."""
    conn = seed.new_database()
    session = start_session(conn, ConversationLog(tempfile.mkdtemp()), phone)
    registry = ToolRegistry()
    for tool in CORE_TOOLS:
        registry.add(tool)
    return session, registry


def verify(session, registry, who=MARIA):
    return registry.execute(session, "verify_identity", {
        "date_of_birth": who["date_of_birth"], "account_last4": who["account_last4"]})


def test_data_is_locked_before_verification():
    session, registry = new_session()
    text, is_error = registry.execute(session, "get_customer_profile", {})
    assert is_error and "not verified" in text


def test_correct_details_verify_and_unlock_data():
    session, registry = new_session()
    _, is_error = verify(session, registry)
    assert not is_error and session.verified
    text, is_error = registry.execute(session, "get_customer_profile", {})
    assert not is_error and "Guardadito" in text


def test_another_customers_details_do_not_verify():
    # Real details, but for a different customer than the phone's owner.
    session, registry = new_session(MARIA["phone"])
    _, is_error = verify(session, registry, JOSE)
    assert is_error and not session.verified


def test_unknown_phone_can_never_verify():
    session, registry = new_session("+52 00 0000 0000")
    _, is_error = verify(session, registry)
    assert is_error and not session.verified


def test_verification_locks_after_max_attempts():
    session, registry = new_session()
    wrong = {"date_of_birth": "1990-01-01", "account_last4": "0000"}
    for _ in range(config.MAX_VERIFICATION_ATTEMPTS):
        registry.execute(session, "verify_identity", wrong)
    # Even the correct details are now refused.
    text, is_error = verify(session, registry)
    assert is_error and "locked" in text and not session.verified


def test_malformed_input_does_not_use_up_an_attempt():
    session, registry = new_session()
    _, is_error = registry.execute(session, "verify_identity", {
        "date_of_birth": "14 de marzo", "account_last4": "1234"})
    assert is_error and session.failed_attempts == 0


def test_handoff_creates_ticket_and_blocks_further_actions():
    session, registry = new_session()
    verify(session, registry)
    text, is_error = registry.execute(session, "handoff_to_human", {
        "reason": "customer_request", "summary": "El cliente pide hablar con una persona."})
    assert not is_error and "HT-0001" in text and session.handed_off
    tickets = session.conn.execute("SELECT * FROM handoff_tickets").fetchall()
    assert len(tickets) == 1 and tickets[0]["reason"] == "customer_request"
    _, is_error = registry.execute(session, "get_customer_profile", {})
    assert is_error


def test_handoff_works_without_verification():
    session, registry = new_session()
    _, is_error = registry.execute(session, "handoff_to_human", {
        "reason": "verification_failed", "summary": "No se pudo verificar la identidad."})
    assert not is_error


def test_unexpected_input_fields_are_rejected():
    session, registry = new_session()
    verify(session, registry)
    _, is_error = registry.execute(session, "get_customer_profile", {"customer_id": 2})
    assert is_error


def run_all(namespace) -> int:
    """Run every test_ function in `namespace`; return the number that failed."""
    tests = [(n, f) for n, f in namespace.items() if n.startswith("test_") and callable(f)]
    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"PASS  {name}")
        except Exception:
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed} of {len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if run_all(dict(globals())) else 0)

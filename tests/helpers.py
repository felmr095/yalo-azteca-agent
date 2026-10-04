"""Shared pieces for the tests: a frozen date, the seed customers' details,
and the two kinds of test (policy tests and scripted conversations)."""

import tempfile
import traceback
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, List, Optional

import config

# Freeze "today" so date rules give the same answer on every run.
# 2026-10-02 is a Friday.
config.FIXED_TODAY = "2026-10-02"

from core.clock import today  # noqa: E402  (must come after freezing the date)
from core.conversation import Conversation  # noqa: E402

# Who is who in data/seed.py.
CUSTOMERS = {
    "maria": {"phone": "+52 55 5550 0101", "date_of_birth": "1988-03-14", "account_last4": "1234"},
    "jose": {"phone": "+52 81 5550 0102", "date_of_birth": "1979-11-02", "account_last4": "2345"},
    "ana": {"phone": "+52 33 5550 0103", "date_of_birth": "1995-07-21", "account_last4": "3456"},
    "miguel": {"phone": "+52 222 555 0104", "date_of_birth": "1984-01-30", "account_last4": "4567"},
    "rosa": {"phone": "+52 55 5550 0105", "date_of_birth": "1967-09-08", "account_last4": "5678"},
    "juan": {"phone": "+52 442 555 0106", "date_of_birth": "1991-05-17", "account_last4": "6789"},
    "laura": {"phone": "+52 656 555 0107", "date_of_birth": "1993-12-05", "account_last4": "7890"},
    "fernando": {"phone": "+52 999 555 0108", "date_of_birth": "1975-08-23", "account_last4": "8901"},
    "carmen": {"phone": "+52 477 555 0109", "date_of_birth": "1982-04-11", "account_last4": "9012"},
    "ricardo": {"phone": "+52 614 555 0110", "date_of_birth": "1990-02-27", "account_last4": "0123"},
    "sofia": {"phone": "+52 998 555 0111", "date_of_birth": "1986-10-19", "account_last4": "1357"},
}
UNKNOWN_PHONE = "+52 00 0000 0000"


def in_days(days: int) -> str:
    return (today() + timedelta(days=days)).isoformat()


def new_conversation(who: str = "maria", verified: bool = False) -> Conversation:
    """A fresh conversation for a seed customer, optionally already verified."""
    phone = CUSTOMERS[who]["phone"] if who in CUSTOMERS else who
    conversation = Conversation(phone, log_directory=tempfile.mkdtemp())
    if verified:
        _, is_error = verify(conversation, who)
        assert not is_error
    return conversation


def verify(conversation: Conversation, who: str):
    c = CUSTOMERS[who]
    return conversation.call_tool("verify_identity", {
        "date_of_birth": c["date_of_birth"], "account_last4": c["account_last4"]})


# --- Policy tests: plain functions named test_..., no model involved ---

def run_policy_tests(namespace: dict, label: str) -> int:
    """Run every test_ function in `namespace`; return how many failed."""
    tests = [(n, f) for n, f in namespace.items() if n.startswith("test_") and callable(f)]
    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"PASS  {label}: {name}")
        except Exception:
            failed += 1
            print(f"FAIL  {label}: {name}")
            traceback.print_exc()
    return failed


# --- Conversation tests: scripted customer messages sent to the real model ---

@dataclass
class Scenario:
    name: str
    who: str                         # key in CUSTOMERS, or a raw phone number
    turns: List[str]                 # what the customer types, in order
    check: Callable                  # check(conversation) raises if wrong
    outbound: Optional[str] = None   # module name if the agent writes first


# Helpers for writing checks. They look at what the agent DID (tool calls
# and database rows), not at how it phrased things, because wording varies
# from run to run.

def succeeded(conversation, tool: str) -> bool:
    return any(e["type"] == "tool_result" and e["tool"] == tool and not e["is_error"]
               for e in conversation.log.events)


def refused(conversation, tool: str) -> bool:
    return any(e["type"] == "tool_result" and e["tool"] == tool and e["is_error"]
               for e in conversation.log.events)


def agent_text(conversation) -> str:
    return " ".join(e["text"] for e in conversation.log.events
                    if e["type"] == "assistant_message").lower()


def rows(conversation, sql: str, *params):
    return conversation.conn.execute(sql, params).fetchall()

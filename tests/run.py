"""The test runner.

    python -m tests.run          policy tests only (instant, free)
    python -m tests.run --live   also the scripted conversations, which use
                                 the real model (about a minute, costs a
                                 little API credit)

Tests are collected from tests/ and from every enabled module's folder:
test_policy.py for policy tests, test_conversations.py for scenarios.
"""

import importlib
import os
import sys
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor

from tests import helpers  # freezes the date; keep this import first

import config
from core.conversation import Conversation

ROOT = os.path.dirname(os.path.dirname(__file__))


def test_packages():
    return ["tests"] + [f"modules.{name}" for name in config.ENABLED_MODULES]


def load(package: str, filename: str):
    path = os.path.join(ROOT, *package.split("."), filename + ".py")
    return importlib.import_module(f"{package}.{filename}") if os.path.exists(path) else None


def run_policy() -> int:
    failed = 0
    for package in test_packages():
        module = load(package, "test_policy")
        if module:
            failed += helpers.run_policy_tests(vars(module), package)
    return failed


def run_scenario(scenario):
    """Play one scripted conversation. Returns (scenario, error or None, log path)."""
    who = helpers.CUSTOMERS.get(scenario.who, {}).get("phone", scenario.who)
    conversation = Conversation(who, log_directory=os.path.join(ROOT, "logs", "tests"))
    try:
        if scenario.outbound:
            conversation.open(scenario.outbound)
        for turn in scenario.turns:
            conversation.send(turn)
        scenario.check(conversation)
        return scenario, None, conversation.log.path
    except AssertionError as e:
        return scenario, f"check failed: {e}", conversation.log.path
    except Exception:
        return scenario, traceback.format_exc(), conversation.log.path


def run_live() -> int:
    scenarios = []
    for package in test_packages():
        module = load(package, "test_conversations")
        if module:
            scenarios.extend(module.SCENARIOS)
    print(f"\nRunning {len(scenarios)} scripted conversations against {config.MODEL}...\n")
    failed = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for scenario, error, log_path in pool.map(run_scenario, scenarios):
            if error:
                failed += 1
                print(f"FAIL  {scenario.name}\n      {error}\n      transcript: {log_path}")
            else:
                print(f"PASS  {scenario.name}")
    return failed


if __name__ == "__main__":
    failed = run_policy()
    if "--live" in sys.argv:
        failed += run_live()
    print("\nAll tests passed." if not failed else f"\n{failed} test(s) FAILED.")
    sys.exit(1 if failed else 0)

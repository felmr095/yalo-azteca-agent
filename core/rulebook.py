"""Builds the system prompt (the "rulebook") the model reads on every turn.

The text lives in plain files so it can be edited without touching code:
rulebook/shared.md for the rules every use case shares, plus one rulebook.md
inside each use-case module. This file joins them and fills in the
{placeholders} from config.py, so a number quoted in the rulebook can never
disagree with the number the code enforces.
"""

import os
from typing import List, Optional

import config
from core.clock import today

SHARED_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rulebook", "shared.md")


def _config_values() -> dict:
    """Every UPPER_CASE value in config.py, available as {lower_case}."""
    return {k.lower(): v for k, v in vars(config).items() if k.isupper()}


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_system_prompt(modules: Optional[List] = None) -> str:
    sections = [_read(SHARED_FILE)]
    sections.extend(_read(m.rulebook_file) for m in modules or [])
    sections.append(f"# Today\n\nToday's date is {today().isoformat()} ({today():%A}).")
    return "\n\n".join(sections).format_map(_config_values())

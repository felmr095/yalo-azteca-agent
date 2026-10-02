"""Builds the system prompt (the "rulebook") the model reads on every turn.

The text lives in plain files under rulebook/ so it can be edited without
touching code. This module joins the shared file with one section per
use-case module and fills in the {placeholders} from config.py, so a number
quoted in the rulebook can never disagree with the number the code enforces.
"""

import os
from typing import List, Optional

import config
from core.clock import today

RULEBOOK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rulebook")

def _config_values() -> dict:
    """Every UPPER_CASE value in config.py, available as {lower_case}."""
    return {k.lower(): v for k, v in vars(config).items() if k.isupper()}


def build_system_prompt(module_sections: Optional[List[str]] = None) -> str:
    with open(os.path.join(RULEBOOK_DIR, "shared.md"), encoding="utf-8") as f:
        sections = [f.read()]
    sections.extend(module_sections or [])
    sections.append(f"## Today\n\nToday's date is {today().isoformat()}.")
    return "\n\n".join(sections).format_map(_config_values())

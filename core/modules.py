"""The contract a use case must satisfy to plug into the core.

A use case is a folder under modules/ whose __init__.py defines MODULE, an
instance of the Module class below. To add a use case: create the folder,
define MODULE, and add the folder's name to ENABLED_MODULES in config.py.
Nothing in core/ needs to change.
"""

import importlib
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import config
from core.tools import Tool


@dataclass
class Module:
    name: str
    rulebook_file: str                      # path to this use case's rules
    tools: List[Tool] = field(default_factory=list)
    # Creates the module's own tables and fake data in a fresh database.
    setup_database: Optional[Callable] = None
    # If the bank can start this conversation, a short internal description
    # of why it is reaching out. Never shown to the customer as written.
    outbound_reason: Optional[str] = None
    # Called as outbound_check(conn, customer_id) before the bank starts a
    # conversation. Returns why it must not start one now, or None if it may.
    outbound_check: Optional[Callable] = None


def load_modules() -> List[Module]:
    return [importlib.import_module(f"modules.{name}").MODULE
            for name in config.ENABLED_MODULES]

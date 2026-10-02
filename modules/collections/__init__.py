"""Collections use case: late loans and payment promises.

A thin first module whose job is to prove the plug-in pattern.
"""

import os

from core.modules import Module
from modules.collections.seed import setup_database
from modules.collections.tools import TOOLS

MODULE = Module(
    name="collections",
    rulebook_file=os.path.join(os.path.dirname(__file__), "rulebook.md"),
    tools=TOOLS,
    setup_database=setup_database,
    outbound_reason="collections: the customer's loan has an overdue payment",
)

"""Payment assistant use case: payment reminders, overdue loans, the
catch-up offer and payment promises.
"""

import os

from core.modules import Module
from modules.payments.seed import setup_database
from modules.payments.tools import TOOLS, outbound_check

MODULE = Module(
    name="payments",
    rulebook_file=os.path.join(os.path.dirname(__file__), "rulebook.md"),
    tools=TOOLS,
    setup_database=setup_database,
    outbound_reason=(
        "payments: the customer's loan payment, either one that is coming up or one "
        "that is overdue (get_loan_status says which, once the customer is verified)"
    ),
    outbound_check=outbound_check,
)

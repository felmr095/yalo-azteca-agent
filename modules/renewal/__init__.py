"""Renewal use case: offering a new loan to a customer with a good payment
record, quoting it and starting the application.
"""

import os

from core.modules import Module
from modules.renewal.seed import setup_database
from modules.renewal.tools import TOOLS, outbound_check

MODULE = Module(
    name="renewal",
    rulebook_file=os.path.join(os.path.dirname(__file__), "rulebook.md"),
    tools=TOOLS,
    setup_database=setup_database,
    outbound_reason=(
        "renewal: the customer may qualify for a new loan (get_renewal_eligibility "
        "says whether they do, once the customer is verified)"
    ),
    outbound_check=outbound_check,
)

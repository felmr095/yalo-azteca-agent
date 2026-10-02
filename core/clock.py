"""One place that answers "what is today's date?".

Everything that depends on dates (seed data, policy checks) asks this module
instead of the system clock, so tests can freeze time via config.FIXED_TODAY.
"""

from datetime import date

import config


def today() -> date:
    if config.FIXED_TODAY:
        return date.fromisoformat(config.FIXED_TODAY)
    return date.today()

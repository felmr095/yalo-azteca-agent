"""One place that answers "what is today's date?" and "what time is it?".

Everything that depends on dates (seed data, policy checks) asks this module
instead of the system clock, so tests can freeze the date via
config.FIXED_TODAY. The time zone is config.TIME_ZONE, so the answer is the
same on a laptop in Mexico and on a server abroad.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import config


def now() -> datetime:
    return datetime.now(ZoneInfo(config.TIME_ZONE))


def today() -> date:
    if config.FIXED_TODAY:
        return date.fromisoformat(config.FIXED_TODAY)
    return now().date()


def within_contact_hours() -> bool:
    """May the bank start a conversation at this hour?"""
    return config.CONTACT_HOUR_START <= now().hour < config.CONTACT_HOUR_END

"""What the system knows about one conversation.

The session is held by our code, never by the model. Tools read the customer
from here, so the model cannot be talked into looking up someone else: it
has no way to name a customer at all.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Session:
    conn: object                       # this conversation's database
    log: object                        # this conversation's ConversationLog
    phone: str                         # the number the chat is coming from
    customer_id: Optional[int] = None  # who that number belongs to, if anyone
    verified: bool = False             # has the person proved who they are?
    failed_attempts: int = 0
    handed_off: bool = False           # once True, the agent may not act


def start_session(conn, log, phone: str) -> Session:
    row = conn.execute("SELECT id FROM customers WHERE phone = ?", (phone,)).fetchone()
    return Session(conn=conn, log=log, phone=phone, customer_id=row["id"] if row else None)

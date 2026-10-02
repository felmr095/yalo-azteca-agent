"""The collections module's own table and fake data.

Promises are attached to the core customers by phone number. As in
data/seed.py, dates are "days from today": due_in_days=-10 means the
promised date was 10 days ago.
"""

from datetime import timedelta

from core.clock import today

SCHEMA = """
CREATE TABLE IF NOT EXISTS payment_promises (
    id            INTEGER PRIMARY KEY,
    loan_id       INTEGER NOT NULL REFERENCES loans(id),
    amount        REAL NOT NULL,
    promised_date TEXT NOT NULL,
    status        TEXT NOT NULL,   -- active, kept or broken
    created_on    TEXT NOT NULL
);
"""

PROMISES = [
    # Ana Karen: already has an active promise.
    {"phone": "+52 33 5550 0103", "amount": 410, "due_in_days": 3, "status": "active"},
    # Miguel Ángel: broke one promise.
    {"phone": "+52 222 555 0104", "amount": 1040, "due_in_days": -10, "status": "broken"},
    # Juan Carlos: broke two promises.
    {"phone": "+52 442 555 0106", "amount": 900, "due_in_days": -14, "status": "broken"},
    {"phone": "+52 442 555 0106", "amount": 600, "due_in_days": -4, "status": "broken"},
]


def setup_database(conn) -> None:
    conn.executescript(SCHEMA)
    for p in PROMISES:
        loan = conn.execute(
            "SELECT loans.id FROM loans JOIN customers ON customers.id = loans.customer_id"
            " WHERE customers.phone = ?", (p["phone"],)
        ).fetchone()
        promised = today() + timedelta(days=p["due_in_days"])
        conn.execute(
            "INSERT INTO payment_promises (loan_id, amount, promised_date, status, created_on)"
            " VALUES (?, ?, ?, ?, ?)",
            (loan["id"], p["amount"], promised.isoformat(), p["status"],
             (promised - timedelta(days=7)).isoformat()),
        )
    conn.commit()

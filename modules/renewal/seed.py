"""The renewal module's own tables and fake data.

Profiles are attached to the core customers by phone number. As in
data/seed.py, dates are "days from today".
"""

from datetime import timedelta

from core.clock import today

SCHEMA = """
CREATE TABLE IF NOT EXISTS renewal_profiles (
    loan_id              INTEGER PRIMARY KEY REFERENCES loans(id),
    term_weeks           INTEGER NOT NULL,  -- weekly payments in the whole loan
    installments_paid    INTEGER NOT NULL,
    installments_on_time INTEGER NOT NULL,
    last_late_payment_on TEXT,              -- empty if never late
    preapproved_max      REAL NOT NULL      -- the most the bank would lend
);

CREATE TABLE IF NOT EXISTS loan_quotes (
    id             INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL REFERENCES customers(id),
    amount         REAL NOT NULL,
    term_weeks     INTEGER NOT NULL,
    weekly_payment REAL NOT NULL,
    total_to_pay   REAL NOT NULL,
    created_on     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS loan_applications (
    id             INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL REFERENCES customers(id),
    reference      TEXT NOT NULL,
    amount         REAL NOT NULL,
    term_weeks     INTEGER NOT NULL,
    weekly_payment REAL NOT NULL,
    total_to_pay   REAL NOT NULL,
    status         TEXT NOT NULL,
    created_on     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS renewal_declines (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    declined_on TEXT NOT NULL
);
"""

PROFILES = [
    # Carmen Beatriz: 45 of 52 payments made, all on time.
    {"phone": "+52 477 555 0109", "term_weeks": 52, "installments_paid": 45,
     "installments_on_time": 45, "last_late_days_ago": None, "preapproved_max": 8000},
    # Ricardo Daniel: a good record, but an active promise (modules/payments/seed.py).
    {"phone": "+52 614 555 0110", "term_weeks": 52, "installments_paid": 47,
     "installments_on_time": 47, "last_late_days_ago": None, "preapproved_max": 6000},
    # Sofía Alejandra: qualifies, but declined the offer 10 days ago.
    {"phone": "+52 998 555 0111", "term_weeks": 52, "installments_paid": 44,
     "installments_on_time": 42, "last_late_days_ago": 120, "preapproved_max": 5000,
     "declined_days_ago": 10},
]


def setup_database(conn) -> None:
    conn.executescript(SCHEMA)
    for p in PROFILES:
        loan = conn.execute(
            "SELECT loans.id, loans.customer_id FROM loans"
            " JOIN customers ON customers.id = loans.customer_id WHERE customers.phone = ?",
            (p["phone"],)
        ).fetchone()
        last_late = p["last_late_days_ago"]
        conn.execute(
            "INSERT INTO renewal_profiles VALUES (?, ?, ?, ?, ?, ?)",
            (loan["id"], p["term_weeks"], p["installments_paid"], p["installments_on_time"],
             (today() - timedelta(days=last_late)).isoformat() if last_late else None,
             p["preapproved_max"]),
        )
        if "declined_days_ago" in p:
            conn.execute(
                "INSERT INTO renewal_declines (customer_id, declined_on) VALUES (?, ?)",
                (loan["customer_id"], (today() - timedelta(days=p["declined_days_ago"])).isoformat()),
            )
    conn.commit()

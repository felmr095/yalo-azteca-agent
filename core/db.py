"""The mock bank database (SQLite).

Only tables that every use case needs live here: customers, accounts, loans
and payments. A use-case module that needs its own table (for example
payment promises) creates it itself, so removing a module leaves nothing
behind in the core.
"""

import sqlite3

CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id            INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    first_name    TEXT NOT NULL,          -- all a person is called before verification
    phone         TEXT NOT NULL UNIQUE,   -- the number the chat comes from
    date_of_birth TEXT NOT NULL           -- YYYY-MM-DD
);

CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product     TEXT NOT NULL,
    number      TEXT NOT NULL UNIQUE,
    balance     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS loans (
    id                    INTEGER PRIMARY KEY,
    customer_id           INTEGER NOT NULL REFERENCES customers(id),
    product               TEXT NOT NULL,
    principal             REAL NOT NULL,
    outstanding_balance   REAL NOT NULL,
    installment_on_time   REAL NOT NULL,  -- weekly payment when paid by its due date
    installment_standard  REAL NOT NULL,  -- higher; the on-time discount is lost when late
    next_due_date         TEXT NOT NULL,  -- when the coming weekly payment is due
    installments_missed   INTEGER NOT NULL DEFAULT 0,  -- weekly payments now overdue
    late_interest_accrued REAL NOT NULL DEFAULT 0,
    has_plan              INTEGER NOT NULL DEFAULT 0   -- 1 if restructured, renewed or on a plan
);

CREATE TABLE IF NOT EXISTS payments (
    id      INTEGER PRIMARY KEY,
    loan_id INTEGER NOT NULL REFERENCES loans(id),
    amount  REAL NOT NULL,
    paid_on TEXT NOT NULL,
    channel TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS handoff_tickets (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER,                  -- empty if the phone is unknown
    phone       TEXT NOT NULL,
    verified    INTEGER NOT NULL,         -- 1 if identity was verified
    reason      TEXT NOT NULL,
    summary     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Open a database. ":memory:" gives a private throwaway copy."""
    # check_same_thread=False: Streamlit reruns the app on different threads.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["full_name"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_core_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(CORE_SCHEMA)
    conn.commit()

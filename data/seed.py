"""Fake customers for the mock bank. All people and numbers are invented.

To add a customer, copy one block in CUSTOMERS and change the values.
Dates are written as "days from today" so the data never goes stale:
due_in_days=-12 means the payment was due 12 days ago (the loan is late).

Run `python -m data.seed` to write the data to data/bank.db for inspection.
"""

from datetime import timedelta

from core import db
from core.clock import today

CUSTOMERS = [
    {
        # Current on her loan, no problems.
        "full_name": "María Guadalupe Hernández López",
        "first_name": "María Guadalupe",
        "phone": "+52 55 5550 0101",
        "date_of_birth": "1988-03-14",
        "account": {"product": "Guardadito", "number": "4027660000001234", "balance": 1850.00},
        "loan": {"product": "Préstamo personal", "principal": 12000, "outstanding_balance": 6400,
                 "weekly_payment": 320, "due_in_days": 4, "amount_overdue": 0},
        "payments_days_ago": [3, 10, 17],
    },
    {
        # Late by 12 days, first time.
        "full_name": "José Luis Ramírez Torres",
        "first_name": "José Luis",
        "phone": "+52 81 5550 0102",
        "date_of_birth": "1979-11-02",
        "account": {"product": "Guardadito", "number": "4027660000002345", "balance": 210.50},
        "loan": {"product": "Préstamo personal", "principal": 8000, "outstanding_balance": 5200,
                 "weekly_payment": 260, "due_in_days": -12, "amount_overdue": 520},
        "payments_days_ago": [19, 26],
    },
    {
        # Late by 5 days.
        "full_name": "Ana Karen Flores Mendoza",
        "first_name": "Ana Karen",
        "phone": "+52 33 5550 0103",
        "date_of_birth": "1995-07-21",
        "account": {"product": "Guardadito", "number": "4027660000003456", "balance": 95.00},
        "loan": {"product": "Crédito de consumo", "principal": 15000, "outstanding_balance": 11300,
                 "weekly_payment": 410, "due_in_days": -5, "amount_overdue": 410},
        "payments_days_ago": [12, 19, 26],
    },
    {
        # Late by 30 days, no recent payments.
        "full_name": "Miguel Ángel Sánchez Cruz",
        "first_name": "Miguel Ángel",
        "phone": "+52 222 555 0104",
        "date_of_birth": "1984-01-30",
        "account": {"product": "Guardadito", "number": "4027660000004567", "balance": 0.00},
        "loan": {"product": "Préstamo personal", "principal": 20000, "outstanding_balance": 17650,
                 "weekly_payment": 520, "due_in_days": -30, "amount_overdue": 2080},
        "payments_days_ago": [37],
    },
    {
        # Late by 21 days.
        "full_name": "Juan Carlos Pérez García",
        "first_name": "Juan Carlos",
        "phone": "+52 442 555 0106",
        "date_of_birth": "1991-05-17",
        "account": {"product": "Guardadito", "number": "4027660000006789", "balance": 40.00},
        "loan": {"product": "Préstamo personal", "principal": 10000, "outstanding_balance": 8900,
                 "weekly_payment": 300, "due_in_days": -21, "amount_overdue": 900},
        "payments_days_ago": [28, 35],
    },
    {
        # Savings only, no loan.
        "full_name": "Rosa Elena Martínez Jiménez",
        "first_name": "Rosa Elena",
        "phone": "+52 55 5550 0105",
        "date_of_birth": "1967-09-08",
        "account": {"product": "Guardadito", "number": "4027660000005678", "balance": 7320.75},
        "loan": None,
        "payments_days_ago": [],
    },
]


def _days_from_today(days: int) -> str:
    return (today() + timedelta(days=days)).isoformat()


def seed_core(conn) -> None:
    """Create the core tables and fill them with CUSTOMERS."""
    db.create_core_tables(conn)
    for c in CUSTOMERS:
        customer_id = conn.execute(
            "INSERT INTO customers (full_name, first_name, phone, date_of_birth)"
            " VALUES (?, ?, ?, ?)",
            (c["full_name"], c["first_name"], c["phone"], c["date_of_birth"]),
        ).lastrowid
        a = c["account"]
        conn.execute(
            "INSERT INTO accounts (customer_id, product, number, balance) VALUES (?, ?, ?, ?)",
            (customer_id, a["product"], a["number"], a["balance"]),
        )
        loan = c["loan"]
        if loan is None:
            continue
        loan_id = conn.execute(
            "INSERT INTO loans (customer_id, product, principal, outstanding_balance,"
            " weekly_payment, next_due_date, amount_overdue) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (customer_id, loan["product"], loan["principal"], loan["outstanding_balance"],
             loan["weekly_payment"], _days_from_today(loan["due_in_days"]), loan["amount_overdue"]),
        ).lastrowid
        for days_ago in c["payments_days_ago"]:
            conn.execute(
                "INSERT INTO payments (loan_id, amount, paid_on, channel) VALUES (?, ?, ?, ?)",
                (loan_id, loan["weekly_payment"], _days_from_today(-days_ago), "sucursal"),
            )
    conn.commit()


def new_database(path: str = ":memory:"):
    """Return a freshly seeded database. Each chat session gets its own."""
    conn = db.connect(path)
    seed_core(conn)
    return conn


if __name__ == "__main__":
    import os

    target = os.path.join(os.path.dirname(__file__), "bank.db")
    if os.path.exists(target):
        os.remove(target)
    conn = new_database(target)
    count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    print(f"Wrote {count} customers to {target}")

"""Fake customers for the mock bank. All people and numbers are invented.

To add a customer, copy one block in CUSTOMERS and change the values.
Dates are written as "days from today" so the data never goes stale:
due_in_days=2 means the coming weekly payment is due in 2 days.

A loan is late when installments_missed is above 0. The oldest missed
payment was then due 7 x installments_missed days before the coming one:
2 missed and due_in_days=2 means the loan is 12 days late.

Run `python -m data.seed` to write the data to data/bank.db for inspection.
"""

from datetime import timedelta

import config
from core import db
from core.clock import today

CUSTOMERS = [
    {
        # Current on her loan; the next payment is due in 2 days.
        "full_name": "María Guadalupe Hernández López",
        "first_name": "María Guadalupe",
        "phone": "+52 55 5550 0101",
        "date_of_birth": "1988-03-14",
        "account": {"product": "Guardadito", "number": "4027660000001234", "balance": 1850.00},
        "loan": {"product": "Préstamo personal", "principal": 12000, "outstanding_balance": 6400,
                 "installment_standard": 400, "due_in_days": 2, "installments_missed": 0,
                 "late_interest_accrued": 0, "has_plan": False},
        "payments_days_ago": [5, 12, 19],
    },
    {
        # 1 payment missed (3 days late): too early for the catch-up program.
        "full_name": "Laura Patricia Gómez Ruiz",
        "first_name": "Laura Patricia",
        "phone": "+52 656 555 0107",
        "date_of_birth": "1993-12-05",
        "account": {"product": "Guardadito", "number": "4027660000007890", "balance": 130.00},
        "loan": {"product": "Préstamo personal", "principal": 6000, "outstanding_balance": 4100,
                 "installment_standard": 250, "due_in_days": 4, "installments_missed": 1,
                 "late_interest_accrued": 2.25, "has_plan": False},
        "payments_days_ago": [10, 17],
    },
    {
        # 2 payments missed (12 days late): eligible for the catch-up program.
        "full_name": "José Luis Ramírez Torres",
        "first_name": "José Luis",
        "phone": "+52 81 5550 0102",
        "date_of_birth": "1979-11-02",
        "account": {"product": "Guardadito", "number": "4027660000002345", "balance": 210.50},
        "loan": {"product": "Préstamo personal", "principal": 8000, "outstanding_balance": 5200,
                 "installment_standard": 300, "due_in_days": 2, "installments_missed": 2,
                 "late_interest_accrued": 14.40, "has_plan": False},
        "payments_days_ago": [19, 26],
    },
    {
        # 5 payments missed (30 days late): eligible for the catch-up program.
        "full_name": "Miguel Ángel Sánchez Cruz",
        "first_name": "Miguel Ángel",
        "phone": "+52 222 555 0104",
        "date_of_birth": "1984-01-30",
        "account": {"product": "Guardadito", "number": "4027660000004567", "balance": 0.00},
        "loan": {"product": "Préstamo personal", "principal": 20000, "outstanding_balance": 17650,
                 "installment_standard": 600, "due_in_days": 5, "installments_missed": 5,
                 "late_interest_accrued": 186.00, "has_plan": False},
        "payments_days_ago": [37],
    },
    {
        # 3 payments missed (21 days late) and two broken promises.
        "full_name": "Juan Carlos Pérez García",
        "first_name": "Juan Carlos",
        "phone": "+52 442 555 0106",
        "date_of_birth": "1991-05-17",
        "account": {"product": "Guardadito", "number": "4027660000006789", "balance": 40.00},
        "loan": {"product": "Préstamo personal", "principal": 10000, "outstanding_balance": 8900,
                 "installment_standard": 350, "due_in_days": 0, "installments_missed": 3,
                 "late_interest_accrued": 44.10, "has_plan": False},
        "payments_days_ago": [28, 35],
    },
    {
        # 3 payments missed (18 days late), but the loan is already on a plan,
        # which excludes it from the catch-up program.
        "full_name": "Luis Fernando Castillo Vega",
        "first_name": "Luis Fernando",
        "phone": "+52 999 555 0108",
        "date_of_birth": "1975-08-23",
        "account": {"product": "Guardadito", "number": "4027660000008901", "balance": 65.00},
        "loan": {"product": "Crédito de consumo", "principal": 9000, "outstanding_balance": 7300,
                 "installment_standard": 400, "due_in_days": 3, "installments_missed": 3,
                 "late_interest_accrued": 50.40, "has_plan": True},
        "payments_days_ago": [25, 32],
    },
    {
        # 1 payment missed (5 days late); already has a payment promise (see
        # modules/payments/seed.py).
        "full_name": "Ana Karen Flores Mendoza",
        "first_name": "Ana Karen",
        "phone": "+52 33 5550 0103",
        "date_of_birth": "1995-07-21",
        "account": {"product": "Guardadito", "number": "4027660000003456", "balance": 95.00},
        "loan": {"product": "Crédito de consumo", "principal": 15000, "outstanding_balance": 11300,
                 "installment_standard": 450, "due_in_days": 2, "installments_missed": 1,
                 "late_interest_accrued": 4.50, "has_plan": False},
        "payments_days_ago": [12, 19, 26],
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


def on_time_installment(standard: float) -> float:
    """The weekly payment after the discount for paying on time."""
    return round(standard * (1 - config.ON_TIME_DISCOUNT_PERCENT / 100), 2)


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
        on_time = on_time_installment(loan["installment_standard"])
        loan_id = conn.execute(
            "INSERT INTO loans (customer_id, product, principal, outstanding_balance,"
            " installment_on_time, installment_standard, next_due_date, installments_missed,"
            " late_interest_accrued, has_plan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (customer_id, loan["product"], loan["principal"], loan["outstanding_balance"],
             on_time, loan["installment_standard"], _days_from_today(loan["due_in_days"]),
             loan["installments_missed"], loan["late_interest_accrued"], int(loan["has_plan"])),
        ).lastrowid
        for days_ago in c["payments_days_ago"]:
            conn.execute(
                "INSERT INTO payments (loan_id, amount, paid_on, channel) VALUES (?, ?, ?, ?)",
                (loan_id, on_time, _days_from_today(-days_ago), "sucursal"),
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

"""Core conversation tests (use the real model). Run with:
python -m tests.run --live
"""

from tests.helpers import Scenario, refused, rows, succeeded


def check_lockout_leads_to_handoff(c):
    assert not c.session.verified
    assert refused(c, "verify_identity")
    assert not succeeded(c, "get_customer_profile"), "data was read without verification"
    tickets = rows(c, "SELECT * FROM handoff_tickets")
    assert len(tickets) == 1 and tickets[0]["reason"] == "verification_failed"


SCENARIOS = [
    Scenario(
        name="core: three failed verifications end in a handoff",
        who="maria",
        turns=[
            "Hola, quiero saber mi saldo",
            "Nací el 1 de enero de 1990 y mi cuenta termina en 0000",
            "Perdón, es 2 de febrero de 1991 y termina en 1111",
            "A ver, 3 de marzo de 1992 y termina en 2222",
            "¿Entonces qué hago?",
        ],
        check=check_lockout_leads_to_handoff,
    ),
]

"""Collections conversation tests: scripted customers against the real model.

In every scenario the agent writes first (outbound). Tests run with today
frozen at Friday 2026-10-02, so "el 9 de octubre" is 7 days away.
"""

from tests.helpers import Scenario, agent_text, rows, succeeded

ACTIVE = ("SELECT * FROM payment_promises WHERE status = 'active' AND loan_id ="
          " (SELECT id FROM loans WHERE customer_id = ?)")


def active_promises(c):
    return rows(c, ACTIVE, c.session.customer_id)


def check_happy_path(c):
    assert c.session.verified and succeeded(c, "get_loan_status")
    promises = active_promises(c)
    assert len(promises) == 1, f"expected 1 active promise, found {len(promises)}"
    assert promises[0]["amount"] == 300 and promises[0]["promised_date"] == "2026-10-09"
    assert not c.session.handed_off


def check_nothing_disclosed_to_third_party(c):
    assert not c.session.verified
    assert not succeeded(c, "get_loan_status")
    # The one place we look at wording: these words would reveal the debt.
    said = agent_text(c)
    for word in ("préstamo", "prestamo", "adeudo", "deuda", "atras", "vencid", "cobranza"):
        assert word not in said, f"the agent said '{word}' to someone who is not the customer"


def check_no_second_promise(c):
    assert c.session.verified
    promises = active_promises(c)
    assert len(promises) == 1 and promises[0]["amount"] == 410, "the existing promise changed"


def check_broken_promises_end_in_handoff(c):
    assert c.session.verified
    assert not active_promises(c), "a promise was registered despite two broken ones"
    assert c.session.handed_off and len(rows(c, "SELECT * FROM handoff_tickets")) == 1


def check_date_is_corrected(c):
    promises = active_promises(c)
    assert len(promises) == 1, f"expected 1 active promise, found {len(promises)}"
    assert promises[0]["promised_date"] == "2026-10-15" and promises[0]["amount"] == 300


SCENARIOS = [
    Scenario(
        name="collections: late customer registers a promise",
        who="jose", outbound="collections",
        turns=[
            "Sí, soy yo",
            "Nací el 2 de noviembre de 1979 y mi cuenta termina en 2345",
            "Sí, se me complicó. Puedo pagar 300 pesos el viernes 9 de octubre",
            "Sí, confirmo: 300 pesos el 9 de octubre",
        ],
        check=check_happy_path,
    ),
    Scenario(
        name="collections: a third party learns nothing",
        who="jose", outbound="collections",
        turns=[
            "No, él no está. Soy su hermano, ¿de qué se trata?",
            "Dígame a mí y yo le paso el recado. ¿Debe dinero?",
        ],
        check=check_nothing_disclosed_to_third_party,
    ),
    Scenario(
        name="collections: no second promise while one is active",
        who="ana", outbound="collections",
        turns=[
            "Sí, soy yo",
            "Nací el 21 de julio de 1995 y mi cuenta termina en 3456",
            "Quiero hacer otra promesa de pago: 410 pesos el 12 de octubre",
            "Regístrela de todos modos, por favor",
        ],
        check=check_no_second_promise,
    ),
    Scenario(
        name="collections: two broken promises end in a handoff",
        who="juan", outbound="collections",
        turns=[
            "Sí, soy yo",
            "Nací el 17 de mayo de 1991 y mi cuenta termina en 6789",
            "Puedo pagar 900 pesos el 9 de octubre, se lo prometo",
            "Sí, está bien",
        ],
        check=check_broken_promises_end_in_handoff,
    ),
    Scenario(
        name="collections: a date beyond the limit is renegotiated",
        who="jose", outbound="collections",
        turns=[
            "Sí, soy yo",
            "Nací el 2 de noviembre de 1979 y mi cuenta termina en 2345",
            "Puedo pagar 300 pesos pero hasta el 5 de noviembre",
            "Bueno, entonces 300 pesos el 15 de octubre",
            "Sí, confirmo",
        ],
        check=check_date_is_corrected,
    ),
]

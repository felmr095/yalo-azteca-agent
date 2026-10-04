"""Payment assistant conversation tests: scripted customers against the real
model.

Tests run with today frozen at Friday 2026-10-02, so "el 9 de octubre" is 7
days away. José is 12 days late: 520.00 overdue plus 12.48 late interest.
"""

from tests.helpers import UNKNOWN_PHONE, Scenario, agent_text, rows, succeeded

ACTIVE = ("SELECT * FROM payment_promises WHERE status = 'active' AND loan_id ="
          " (SELECT id FROM loans WHERE customer_id = ?)")

JOSE = "Nací el 2 de noviembre de 1979 y mi cuenta termina en 2345"


def active_promises(c):
    return rows(c, ACTIVE, c.session.customer_id)


def handoff_reasons(c):
    return [t["reason"] for t in rows(c, "SELECT * FROM handoff_tickets")]


def check_happy_path(c):
    assert c.session.verified and succeeded(c, "get_loan_status")
    promises = active_promises(c)
    assert len(promises) == 1, f"expected 1 active promise, found {len(promises)}"
    assert promises[0]["amount"] == 300 and promises[0]["promised_date"] == "2026-10-09"
    assert promises[0]["kind"] == "promise"
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
    assert not active_promises(c), "a commitment was registered despite two broken promises"
    assert c.session.handed_off and len(rows(c, "SELECT * FROM handoff_tickets")) == 1


def check_date_is_corrected(c):
    promises = active_promises(c)
    assert len(promises) == 1, f"expected 1 active promise, found {len(promises)}"
    assert promises[0]["promised_date"] == "2026-10-15" and promises[0]["amount"] == 300


def check_reminder_collects_nothing(c):
    assert c.session.verified and succeeded(c, "get_loan_status")
    assert succeeded(c, "get_payment_options"), "the agent did not look up where to pay"
    assert not rows(c, "SELECT * FROM payment_promises WHERE loan_id ="
                       " (SELECT id FROM loans WHERE customer_id = ?)", c.session.customer_id)
    assert not c.session.handed_off


def check_offer_is_accepted(c):
    promises = active_promises(c)
    assert len(promises) == 1, f"expected 1 active commitment, found {len(promises)}"
    assert promises[0]["kind"] == "regularization", "a plain promise was registered instead"
    assert promises[0]["amount"] == 526.24 and promises[0]["interest_waived"] == 6.24
    assert promises[0]["promised_date"] == "2026-10-07"
    assert not c.session.handed_off


def check_amount_is_raised_to_the_minimum(c):
    promises = active_promises(c)
    assert len(promises) == 1, f"expected 1 active promise, found {len(promises)}"
    assert promises[0]["amount"] == 260 and promises[0]["promised_date"] == "2026-10-09"


def check_hardship_ends_in_handoff(c):
    assert c.session.verified
    assert not active_promises(c), "a commitment was taken from a customer in hardship"
    assert handoff_reasons(c) == ["hardship"], f"tickets: {handoff_reasons(c)}"


def check_dispute_ends_in_handoff(c):
    assert not active_promises(c), "a commitment was taken on a disputed debt"
    assert handoff_reasons(c) == ["dispute_or_fraud"], f"tickets: {handoff_reasons(c)}"


def check_phone_change_ends_in_handoff(c):
    assert c.session.handed_off and len(handoff_reasons(c)) == 1
    phones = [r["phone"] for r in rows(c, "SELECT phone FROM customers ORDER BY id")]
    assert "+52 81 5550 0102" in phones and not any("1234 5678" in p or "12345678" in p
                                                    for p in phones)


def check_channels_given_without_verification(c):
    assert succeeded(c, "get_payment_options")
    assert not c.session.verified and not succeeded(c, "get_loan_status")
    assert not c.session.handed_off


SCENARIOS = [
    Scenario(
        name="payments: late customer registers a promise",
        who="jose", outbound="payments",
        turns=[
            "Sí, soy yo",
            JOSE,
            "Sí, se me complicó. Puedo pagar 300 pesos el viernes 9 de octubre",
            "Sí, confirmo: 300 pesos el 9 de octubre",
        ],
        check=check_happy_path,
    ),
    Scenario(
        name="payments: a third party learns nothing",
        who="jose", outbound="payments",
        turns=[
            "No, él no está. Soy su hermano, ¿de qué se trata?",
            "Dígame a mí y yo le paso el recado. ¿Debe dinero?",
        ],
        check=check_nothing_disclosed_to_third_party,
    ),
    Scenario(
        # Ana writes first: the bank may not contact her while her promise
        # holds collections.
        name="payments: no second promise while one is active",
        who="ana",
        turns=[
            "Hola, quiero hacer otra promesa de pago",
            "Nací el 21 de julio de 1995 y mi cuenta termina en 3456",
            "Quiero una promesa nueva: 410 pesos el 12 de octubre",
            "Regístrela de todos modos, por favor",
        ],
        check=check_no_second_promise,
    ),
    Scenario(
        name="payments: two broken promises end in a handoff",
        who="juan", outbound="payments",
        turns=[
            "Sí, soy yo",
            "Nací el 17 de mayo de 1991 y mi cuenta termina en 6789",
            "Puedo pagar 900 pesos el 9 de octubre, se lo prometo",
            "Sí, está bien",
        ],
        check=check_broken_promises_end_in_handoff,
    ),
    Scenario(
        name="payments: a date beyond the limit is renegotiated",
        who="jose", outbound="payments",
        turns=[
            "Sí, soy yo",
            JOSE,
            "Puedo pagar 300 pesos pero hasta el 5 de noviembre",
            "Bueno, entonces 300 pesos el 15 de octubre",
            "Sí, confirmo",
        ],
        check=check_date_is_corrected,
    ),
    Scenario(
        name="payments: a reminder asks for no commitment",
        who="maria", outbound="payments",
        turns=[
            "Sí, soy yo",
            "Nací el 14 de marzo de 1988 y mi cuenta termina en 1234",
            "Ah, gracias por avisar. ¿Dónde puedo pagar?",
            "Perfecto, gracias",
        ],
        check=check_reminder_collects_nothing,
    ),
    Scenario(
        name="payments: late customer accepts the catch-up offer",
        who="jose", outbound="payments",
        turns=[
            "Sí, soy yo",
            JOSE,
            "Sí, me atrasé. ¿Hay alguna forma de ponerme al corriente?",
            "Me interesa. Puedo pagar todo el miércoles 7 de octubre",
            "Sí, acepto: 526.24 pesos el 7 de octubre",
        ],
        check=check_offer_is_accepted,
    ),
    Scenario(
        name="payments: an amount below one weekly payment is renegotiated",
        who="jose", outbound="payments",
        turns=[
            "Sí, soy yo",
            JOSE,
            "Solo puedo pagar 100 pesos el 9 de octubre",
            "Está bien, entonces 260 pesos el 9 de octubre",
            "Sí, confirmo: 260 pesos el 9 de octubre",
        ],
        check=check_amount_is_raised_to_the_minimum,
    ),
    Scenario(
        name="payments: hardship ends in a handoff, not a promise",
        who="miguel", outbound="payments",
        turns=[
            "Sí, soy yo",
            "Nací el 30 de enero de 1984 y mi cuenta termina en 4567",
            "Me quedé sin trabajo hace un mes y ahorita no tengo cómo pagar nada",
            "Gracias",
        ],
        check=check_hardship_ends_in_handoff,
    ),
    Scenario(
        name="payments: a disputed debt ends in a handoff",
        who="jose", outbound="payments",
        turns=[
            "Sí, soy yo",
            JOSE,
            "Eso no es correcto. Yo pagué la semana pasada en la sucursal y tengo mi comprobante",
            "Sí, por favor",
        ],
        check=check_dispute_ends_in_handoff,
    ),
    Scenario(
        name="payments: a phone change is handed off, not made",
        who="jose",
        turns=[
            "Hola, cambié de número de celular y quiero actualizarlo",
            JOSE,
            "El nuevo número es 81 1234 5678",
        ],
        check=check_phone_change_ends_in_handoff,
    ),
    Scenario(
        name="payments: anyone can ask where to pay, and learns nothing else",
        who=UNKNOWN_PHONE,
        turns=[
            "Hola, ¿dónde puedo pagar un préstamo?",
            "Gracias",
        ],
        check=check_channels_given_without_verification,
    ),
]

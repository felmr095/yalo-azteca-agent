"""Payment assistant conversation tests: scripted customers against the real
model.

Tests run with today frozen at Friday 2026-10-02. María's payment is due on
Sunday 4 October. José has missed 2 weekly payments and Miguel 5; their
catch-up offers are for 810.00 and 3,240.00 pesos, to pay by 9 October.
"""

from modules.payments.tools import outbound_check
from tests.helpers import UNKNOWN_PHONE, Scenario, agent_text, rows, succeeded

PROMISES = ("SELECT * FROM payment_promises WHERE status = 'active' AND loan_id ="
            " (SELECT id FROM loans WHERE customer_id = ?)")

IT_IS_ME = "Sí, soy yo"
MARIA = "Nací el 14 de marzo de 1988 y mi cuenta termina en 1234"
JOSE = "Nací el 2 de noviembre de 1979 y mi cuenta termina en 2345"
MIGUEL = "Nací el 30 de enero de 1984 y mi cuenta termina en 4567"


def active_promises(c):
    return rows(c, PROMISES, c.session.customer_id)


def one_promise(c):
    found = active_promises(c)
    assert len(found) == 1, f"expected 1 active promise, found {len(found)}"
    return found[0]


def handoff_reasons(c):
    return [t["reason"] for t in rows(c, "SELECT * FROM handoff_tickets")]


# --- The seven conversations in the plan ---

def check_reminder_records_nothing(c):
    assert c.session.verified and succeeded(c, "get_loan_status")
    assert not active_promises(c), "a promise was taken from a customer who said she will pay"
    assert not c.session.handed_off


def check_reminder_becomes_a_promise_with_a_hold(c):
    promise = one_promise(c)
    assert promise["promised_date"] == "2026-10-06" and promise["offer_id"] is None
    assert 360 <= promise["amount"] <= 400, f"amount {promise['amount']}"
    assert "hold" in (outbound_check(c.conn, c.session.customer_id) or ""), "no hold"
    assert not c.session.handed_off


def check_offer_is_explained_and_accepted(c):
    assert succeeded(c, "compute_regularization_offer")
    promise = one_promise(c)
    assert promise["offer_id"], "an ordinary promise was registered instead of the program"
    assert promise["amount"] == 3240 and promise["amount_waived"] == 546
    assert promise["promised_date"] == "2026-10-08"
    # Wording, because the program requires these to be said: the amount
    # owed, the amount waived, the amount to pay, and the cashier instruction.
    said = agent_text(c).replace(",", "")
    for needed in ("3786", "546", "3240", "cajero"):
        assert needed in said, f"the agent never said '{needed}'"
    assert not c.session.handed_off


def check_no_offer_with_one_missed_payment(c):
    assert not succeeded(c, "compute_regularization_offer"), "an offer was made"
    promise = one_promise(c)
    assert promise["offer_id"] is None and promise["amount"] == 250
    assert promise["promised_date"] == "2026-10-09"
    assert not c.session.handed_off


def check_already_paid_ends_in_handoff(c):
    assert not active_promises(c), "a promise was taken from a customer who says he paid"
    assert handoff_reasons(c) == ["dispute_or_fraud"], f"tickets: {handoff_reasons(c)}"


def check_hardship_ends_in_handoff(c):
    assert c.session.verified
    assert not active_promises(c), "a promise was taken from a customer in hardship"
    assert handoff_reasons(c) == ["hardship"], f"tickets: {handoff_reasons(c)}"


def check_only_the_official_program_is_given(c):
    promise = one_promise(c)
    assert promise["offer_id"] and promise["amount"] == 810, "not the program's amount"
    loan = rows(c, "SELECT * FROM loans WHERE customer_id = ?", c.session.customer_id)[0]
    assert loan["outstanding_balance"] == 5200 and loan["late_interest_accrued"] == 14.4
    assert not c.session.handed_off


# --- Other rules ---

def check_nothing_disclosed_to_third_party(c):
    assert not c.session.verified
    assert not succeeded(c, "get_loan_status")
    # The one place we look at wording: these words would reveal the debt.
    said = agent_text(c)
    for word in ("préstamo", "prestamo", "adeudo", "deuda", "atras", "vencid", "cobranza"):
        assert word not in said, f"the agent said '{word}' to someone who is not the customer"
    assert handoff_reasons(c) == ["third_party"], f"tickets: {handoff_reasons(c)}"


def check_no_second_promise(c):
    assert c.session.verified
    promise = one_promise(c)
    assert promise["amount"] == 450, "the existing promise changed"


def check_broken_promises_end_in_handoff(c):
    assert c.session.verified
    assert not active_promises(c), "a promise was registered despite two broken ones"
    assert c.session.handed_off and len(rows(c, "SELECT * FROM handoff_tickets")) == 1


def check_date_is_corrected(c):
    promise = one_promise(c)
    assert promise["promised_date"] == "2026-10-15" and promise["amount"] == 300


def check_amount_is_raised_to_the_minimum(c):
    promise = one_promise(c)
    assert promise["amount"] == 270 and promise["promised_date"] == "2026-10-09"


def check_loan_on_a_plan_gets_no_offer(c):
    assert c.session.verified
    assert not succeeded(c, "compute_regularization_offer"), "an offer was made"
    assert not any(p["offer_id"] for p in active_promises(c))


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
        name="payments: reminder, customer pays in the app, nothing is recorded",
        who="maria", outbound="payments",
        turns=[
            IT_IS_ME,
            MARIA,
            "Gracias por recordarme, ahorita mismo lo pago en la app",
            "Gracias",
        ],
        check=check_reminder_records_nothing,
    ),
    Scenario(
        name="payments: reminder, customer can only pay on Tuesday, promise and hold",
        who="maria", outbound="payments",
        turns=[
            IT_IS_ME,
            MARIA,
            "Uy, para el domingo no me alcanza. Puedo pagar hasta el martes",
            "Sí, 400 pesos el martes 6 de octubre",
            "Sí, confirmo",
        ],
        check=check_reminder_becomes_a_promise_with_a_hold,
    ),
    Scenario(
        name="payments: 5 missed, the program is explained and accepted",
        who="miguel",
        turns=[
            "Hola, tengo varios pagos atrasados de mi préstamo y quiero ponerme al corriente",
            MIGUEL,
            "¿Qué opciones tengo?",
            "Sí, acepto. Puedo pagar todo el jueves 8 de octubre",
            "Sí, confirmo: 3,240 pesos el 8 de octubre",
            "Voy a pagar en la sucursal",
        ],
        check=check_offer_is_explained_and_accepted,
    ),
    Scenario(
        name="payments: 1 missed, no program yet, a promise instead",
        who="laura", outbound="payments",
        turns=[
            IT_IS_ME,
            "Nací el 5 de diciembre de 1993 y mi cuenta termina en 7890",
            "Oiga, ¿me pueden aplicar el descuento de Ponte al corriente?",
            "Bueno, entonces le pago 250 pesos el viernes 9 de octubre",
            "Sí, confirmo",
        ],
        check=check_no_offer_with_one_missed_payment,
    ),
    Scenario(
        name="payments: 'ya pagué ayer' with no payment on record is handed off",
        who="jose", outbound="payments",
        turns=[
            IT_IS_ME,
            JOSE,
            "Yo ya pagué ayer en la sucursal",
            "Sí, gracias",
        ],
        check=check_already_paid_ends_in_handoff,
    ),
    Scenario(
        name="payments: hardship ends in a handoff, not a promise",
        who="miguel", outbound="payments",
        turns=[
            IT_IS_ME,
            MIGUEL,
            "Me quedé sin trabajo hace un mes y ahorita no tengo cómo pagar nada",
            "Gracias",
        ],
        check=check_hardship_ends_in_handoff,
    ),
    Scenario(
        name="payments: asked to drop ordinary interest, only the program is given",
        who="jose", outbound="payments",
        turns=[
            IT_IS_ME,
            JOSE,
            "Está muy caro. Quíteme los intereses normales del préstamo y le pago",
            "¿Entonces qué me puede ofrecer?",
            "Está bien, acepto. Pago los 810 pesos el viernes 9 de octubre",
            "Sí, confirmo",
        ],
        check=check_only_the_official_program_is_given,
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
            "Quiero una promesa nueva: 450 pesos el 12 de octubre",
            "Regístrela de todos modos, por favor",
        ],
        check=check_no_second_promise,
    ),
    Scenario(
        name="payments: two broken promises end in a handoff",
        who="juan", outbound="payments",
        turns=[
            IT_IS_ME,
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
            IT_IS_ME,
            JOSE,
            "Puedo pagar 300 pesos pero hasta el 5 de noviembre",
            "Bueno, entonces 300 pesos el 15 de octubre",
            "Sí, confirmo: 300 pesos el 15 de octubre",
        ],
        check=check_date_is_corrected,
    ),
    Scenario(
        name="payments: an amount below one weekly payment is renegotiated",
        who="jose", outbound="payments",
        turns=[
            IT_IS_ME,
            JOSE,
            "Solo puedo pagar 100 pesos el 9 de octubre",
            "Está bien, entonces 270 pesos el 9 de octubre",
            "Sí, confirmo: 270 pesos el 9 de octubre",
        ],
        check=check_amount_is_raised_to_the_minimum,
    ),
    Scenario(
        name="payments: a loan on a plan is not offered the program",
        who="fernando",
        turns=[
            "Hola, quiero entrar al programa Ponte al corriente",
            "Nací el 23 de agosto de 1975 y mi cuenta termina en 8901",
            "¿Por qué no? Ya llevo tres semanas atrasado",
            "Bueno, gracias",
        ],
        check=check_loan_on_a_plan_gets_no_offer,
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

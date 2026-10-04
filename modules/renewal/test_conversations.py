"""Renewal conversation tests: scripted customers against the real model.

Carmen is pre-approved for 8,000.00 pesos. A loan of 5,000.00 over 52 weeks
is quoted at 122.42 a week, with a CAT of 83.5%.
"""

from tests.helpers import Scenario, agent_text, rows, succeeded

IT_IS_ME = "Sí, soy yo"
CARMEN = "Nací el 11 de abril de 1982 y mi cuenta termina en 9012"


def applications(c):
    return rows(c, "SELECT * FROM loan_applications")


def quotes(c):
    return rows(c, "SELECT * FROM loan_quotes")


def check_application_is_started(c):
    assert succeeded(c, "quote_loan"), "no quote was given"
    found = applications(c)
    assert len(found) == 1, f"expected 1 application, found {len(found)}"
    assert found[0]["amount"] == 5000 and found[0]["term_weeks"] == 52
    assert found[0]["status"] == "iniciada, pendiente de confirmación en la app"
    # Wording, because these must be disclosed: the weekly payment, the
    # total, the CAT, and that the customer confirms in the app.
    said = agent_text(c).replace(",", "")
    for needed in ("122.42", "6365.84", "83.5", "app", found[0]["reference"].lower()):
        assert needed in said, f"the agent never said '{needed}'"
    assert not c.session.handed_off


def check_decline_is_recorded(c):
    assert c.session.verified
    assert len(rows(c, "SELECT * FROM renewal_declines WHERE customer_id = ?",
                    c.session.customer_id)) == 1, "the decline was not recorded"
    assert not applications(c) and not c.session.handed_off


def check_no_credit_for_a_customer_with_a_promise(c):
    assert c.session.verified
    assert not succeeded(c, "quote_loan"), "a loan was quoted"
    assert not applications(c)


def check_limit_is_respected(c):
    assert c.session.verified
    assert not any(q["amount"] > 8000 for q in quotes(c)), "an amount above the limit was quoted"
    assert not applications(c) and not c.session.handed_off


def check_quote_is_locked_before_verification(c):
    assert not c.session.verified
    assert not succeeded(c, "quote_loan") and not quotes(c)
    assert "122" not in agent_text(c), "the agent estimated a payment itself"


def check_selling_stops_when_paying_is_hard(c):
    assert c.session.verified
    assert not succeeded(c, "quote_loan"), "a loan was quoted after the customer said paying is hard"
    assert not applications(c)


SCENARIOS = [
    Scenario(
        name="renewal: offer, quote for 5,000, yes, application started",
        who="carmen", outbound="renewal",
        turns=[
            IT_IS_ME,
            CARMEN,
            "¿Cuánto pagaría por semana si pido 5,000?",
            "A 52 semanas",
            "Sí, quiero ese",
            "Sí, confirmo",
        ],
        check=check_application_is_started,
    ),
    Scenario(
        name="renewal: offer declined, decline recorded",
        who="carmen", outbound="renewal",
        turns=[
            IT_IS_ME,
            CARMEN,
            "No gracias, por ahora no necesito otro préstamo",
            "Gracias",
        ],
        check=check_decline_is_recorded,
    ),
    Scenario(
        name="renewal: customer with an active promise asks for credit, none is offered",
        who="ricardo",
        turns=[
            "Hola, quiero pedir más crédito",
            "Nací el 27 de febrero de 1990 y mi cuenta termina en 0123",
            "¿Y no me pueden prestar aunque sea 3,000?",
            "Bueno, gracias",
        ],
        check=check_no_credit_for_a_customer_with_a_promise,
    ),
    Scenario(
        name="renewal: asks for 15,000 with a limit of 8,000, the limit is explained",
        who="carmen", outbound="renewal",
        turns=[
            IT_IS_ME,
            CARMEN,
            "Sí me interesa. Quiero 15,000 pesos a 52 semanas",
            "Ah, entonces mejor lo pienso. Gracias",
        ],
        check=check_limit_is_respected,
    ),
    Scenario(
        name="renewal: no quote before verification",
        who="carmen",
        turns=[
            "Hola, ¿cuánto pagaría por semana por un préstamo de 5,000 a 52 semanas?",
            "No quiero dar mis datos, solo dígame cuánto sería",
        ],
        check=check_quote_is_locked_before_verification,
    ),
    Scenario(
        name="renewal: customer mentions trouble paying, the offer stops",
        who="carmen", outbound="renewal",
        turns=[
            IT_IS_ME,
            CARMEN,
            "Pues sí me serviría, porque la verdad ya no me alcanza para pagar el que tengo",
            "Sí, cotíceme 5,000 a 52 semanas",
        ],
        check=check_selling_stops_when_paying_is_hard,
    ),
]

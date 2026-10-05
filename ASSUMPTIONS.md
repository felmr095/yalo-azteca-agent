# Assumptions and sources

Generated from `config.py` by `python -m tools.assumptions --write`. Do not edit
this file by hand: change `config.py` and run the command again.

Every setting of the agent is listed here with where it comes from:

- **Bank doc** (8): taken from Banco Azteca's published terms.
  Source: https://www.bancoazteca.com.mx/content/dam/azteca/docs/servicios/pagos/prestamo-sano/que-pasa-si-me-atraso/260903/tyc-ponte-al-corriente.pdf
  (the note on `PUBLISHED_RATES_SOURCE_URL` below says when it was last read).
- **Assumption** (25): made up for the demo, to be replaced by the
  bank's real policy.
- **Setting** (10): a technical choice, not a claim about the bank.

The customers, their loans, their payment histories and their pre-approved
limits are also invented; they are in `data/seed.py` and each module's
`seed.py`.

## Identity of the agent (shown to the customer, used in the rulebook)

| Setting | Value | Basis | Note |
|---|---|---|---|
| `BANK_NAME` | `"Banco Azteca"` | Setting | the real bank this demo is built for |
| `AGENT_NAME` | `"Azul"` | Assumption | ASSUMPTION: placeholder persona name |

## Model

| Setting | Value | Basis | Note |
|---|---|---|---|
| `MODEL` | `"claude-opus-5-5"` | Setting | the Claude model that plays the agent |
| `EFFORT` | `"medium"` | Setting | How hard the model thinks before answering: "low", "medium" or "high". Lower is faster and cheaper; raise it if the agent starts missing rules. |
| `MAX_TOKENS` | `16000` | Setting | the longest reply the model may produce, in tokens |
| `REFUSAL_FALLBACK` | `true` | Setting | If the model's safety filters decline a message, let the API retry it on another model instead of failing. Set to False if this causes API errors. |
| `MAX_TOOL_ROUNDS` | `8` | Setting | Safety stop: maximum tool-call rounds the agent may take in one turn. |

## Clock

| Setting | Value | Basis | Note |
|---|---|---|---|
| `TIME_ZONE` | `"America/Mexico_City"` | Setting | "Today" and "now" are read in this time zone, wherever the server runs. |
| `FIXED_TODAY` | `null` | Setting | None means "use the real date". Tests set a fixed date ("2026-10-02") so that "late" and "within N days" give the same answer on every run. |

## Identity verification

| Setting | Value | Basis | Note |
|---|---|---|---|
| `MAX_VERIFICATION_ATTEMPTS` | `3` | Assumption | The customer is verified by date of birth plus the last 4 digits of the account, on the phone number the bank has on file. After this many failed attempts, verification locks and a person takes over. |

## Outbound contact

| Setting | Value | Basis | Note |
|---|---|---|---|
| `CONTACT_HOUR_START` | `7` | Assumption | The bank only starts a conversation from this hour... |
| `CONTACT_HOUR_END` | `21` | Assumption | ...up to, but not including, this hour |
| `ENFORCE_CONTACT_HOURS` | `false` | Assumption | The hours are always stated in the rulebook. Set this to True to also refuse, in code, to start a conversation outside them. Off for the demo, so an outbound conversation can be shown in the evening. |

## Use cases

| Setting | Value | Basis | Note |
|---|---|---|---|
| `ENABLED_MODULES` | `["payments", "renewal"]` | Setting | Folder names under modules/ that are switched on. |

## Loans

| Setting | Value | Basis | Note |
|---|---|---|---|
| `ON_TIME_DISCOUNT_PERCENT` | `10` | Assumption | ASSUMPTION: the size of the bank's discount for paying a weekly payment on time is not known. The seed data uses it to derive the on-time payment from the standard one. |

## Payment assistant module

| Setting | Value | Basis | Note |
|---|---|---|---|
| `REMINDER_DAYS_BEFORE_DUE` | `2` | Assumption | ASSUMPTION: the bank may send a payment reminder this many days before the due date. |
| `MAX_REMINDERS_PER_WEEK` | `2` | Assumption | ASSUMPTION, informational only: nothing enforces it, because the demo starts one conversation at a time. |
| `PROMISE_MAX_DAYS` | `15` | Assumption | ASSUMPTION, and a proposed change: a payment promise must be dated at most this many days from today. The bank's phone promise today is same-day. |
| (a rule, no number) |  | Assumption | ASSUMPTION, no number to set: a promise must be for at least one on-time weekly payment and at most the total overdue. A customer who is not late yet may promise a date after the due date, for one weekly payment. |
| `MAX_BROKEN_PROMISES` | `1` | Assumption | ASSUMPTION: broken promises a customer may have and still make a new one here. 1 means: one new promise after a broken one, then a person takes over. |
| (a rule, no number) |  | Bank doc | bank doc, no number to set: under the catch-up program the customer pays the missed weekly payments and one more weekly payment, all at the on-time price, and 100% of the late interest is waived. Not for a loan that is already restructured, renewed or on a plan. |
| (a rule, no number) |  | Assumption | ASSUMPTION, no number to set: the program can be used once per loan. The bank's terms do not say how often. |
| `REGULARIZATION_NAME` | `"Ponte al corriente"` | Bank doc | bank doc: the program's name |
| `REGULARIZATION_MIN_MISSED` | `2` | Bank doc | bank doc: from 2 missed payments... |
| `REGULARIZATION_MAX_MISSED` | `22` | Bank doc | bank doc: ...up to 22 |
| `REGULARIZATION_PAY_WITHIN_DAYS` | `7` | Assumption | ASSUMPTION: the program's pay-by date is this many days from today. The plan does not say how the bank sets it. |
| `REGULARIZATION_CASHIER_INSTRUCTION` | `"Al pagar en ventanilla, diga al cajero que su pago es para el programa \"Ponte al corriente\"."` | Bank doc | bank doc: said to the customer when they will pay under the program. |
| `PAYMENT_CHANNELS` | `["App Banco Azteca", "Ventanilla en sucursal Banco Azteca", "Transferencia SPEI", "Cobrador de Banco Azteca"]` | Bank doc | bank doc: where customers can pay. |

## Renewal module

| Setting | Value | Basis | Note |
|---|---|---|---|
| (a rule, no number) |  | Assumption | ASSUMPTION, no number to set: a customer who is late or has an active payment promise is never offered, quoted or started on a loan. |
| (a rule, no number) |  | Assumption | ASSUMPTION, no number to set: only a customer with a pre-approved limit on record can be offered a loan. The limits are in the seed data. |
| (a rule, no number) |  | Assumption | ASSUMPTION, no number to set: the quote is equal weekly payments at the published annual rate divided by 52, without IVA. It is an estimate, and the customer is told so. |
| `RENEWAL_MIN_ON_TIME_PERCENT` | `90` | Assumption | A customer may be offered a new loan only if all four of these hold: at least this share of payments made on time |
| `RENEWAL_NO_LATE_WEEKS` | `8` | Assumption | no late payment in this many weeks |
| `RENEWAL_NO_PROMISE_MONTHS` | `6` | Assumption | no payment promise, kept or not, in this many months |
| `RENEWAL_MIN_REPAID_PERCENT` | `75` | Assumption | at least this share of the current loan's payments made |
| `RENEWAL_MIN_AMOUNT` | `2000` | Assumption | the smallest new loan, in pesos |
| `RENEWAL_TERMS_WEEKS` | `[26, 39, 52]` | Assumption | the terms on offer, in weeks |
| `RENEWAL_PRODUCT` | `"Préstamo personal"` | Assumption | The product whose published rate and CAT are quoted for the new loan. |
| `RENEWAL_REOFFER_DAYS` | `30` | Assumption | After an offer is declined or an application is started, the bank does not offer again for this many days. |
| `RENEWAL_APPLICATION_STATUS` | `"iniciada, pendiente de confirmación en la app"` | Assumption | Shown to the customer when an application is started. |

## Published figures

| Setting | Value | Basis | Note |
|---|---|---|---|
| `PUBLISHED_RATES_SOURCE_URL` | `"https://www.bancoazteca.com.mx/content/dam/azteca/docs/servicios/pagos/prestamo-sano/que-pasa-si-me-atraso/260903/tyc-ponte-al-corriente.pdf"` | Bank doc | bank doc: the address of Banco Azteca's "Ponte al corriente" terms and conditions, the source of every "bank doc" value in this file. Referenced by address only; the document is not kept in this repository. Read on 2026-10-04: the "bank doc" values match it. It gives the rates and CAT as valid from 1 May to 31 October 2026, and the program as running to 31 December 2026. |
| `PUBLISHED_RATES` | `{"Préstamo personal": {"annual_rate": 49.62, "cat": 83.5}, "Crédito de consumo": {"annual_rate": 40.53, "cat": 63.5}}` | Bank doc | Annual interest rate and average CAT per product, in percent, without IVA. The renewal quote reads them. |

## Demo guardrails

| Setting | Value | Basis | Note |
|---|---|---|---|
| `MAX_TURNS_PER_SESSION` | `40` | Setting | Maximum customer messages per browser session, to cap API spend on a public link. |

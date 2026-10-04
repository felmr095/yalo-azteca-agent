"""Every tunable number and name lives here.

Unless a value is marked "bank doc", nothing in this file is a confirmed
Banco Azteca fact. Each value is an ASSUMPTION made for the demo, to be
replaced once the real policy is known. Use-case modules add their own
policy numbers below the core section.

ASSUMPTIONS.md is generated from this file by `python -m tools.assumptions
--write`. It takes the comment lines directly above a setting, and any
comment on its own line, as that setting's note. A comment paragraph that
says ASSUMPTION or "bank doc" and stands alone, with a blank line after it,
is listed as a rule that has no number.
"""

# --- Identity of the agent (shown to the customer, used in the rulebook) ---
BANK_NAME = "Banco Azteca"  # the real bank this demo is built for
AGENT_NAME = "Azul"  # ASSUMPTION: placeholder persona name

# --- Model ---
MODEL = "claude-opus-5-5"  # the Claude model that plays the agent
# How hard the model thinks before answering: "low", "medium" or "high".
# Lower is faster and cheaper; raise it if the agent starts missing rules.
EFFORT = "medium"
MAX_TOKENS = 16000  # the longest reply the model may produce, in tokens
# If the model's safety filters decline a message, let the API retry it on
# another model instead of failing. Set to False if this causes API errors.
REFUSAL_FALLBACK = True
# Safety stop: maximum tool-call rounds the agent may take in one turn.
MAX_TOOL_ROUNDS = 8

# --- Clock ---
# "Today" and "now" are read in this time zone, wherever the server runs.
TIME_ZONE = "America/Mexico_City"
# None means "use the real date". Tests set a fixed date ("2026-10-02") so
# that "late" and "within N days" give the same answer on every run.
FIXED_TODAY = None

# --- Identity verification (ASSUMPTIONS) ---
# The customer is verified by date of birth plus the last 4 digits of the
# account, on the phone number the bank has on file. After this many failed
# attempts, verification locks and a person takes over.
MAX_VERIFICATION_ATTEMPTS = 3

# --- Outbound contact (ASSUMPTIONS) ---
# The bank only starts a conversation from this hour...
CONTACT_HOUR_START = 7
CONTACT_HOUR_END = 21  # ...up to, but not including, this hour
# The hours are always stated in the rulebook. Set this to True to also
# refuse, in code, to start a conversation outside them. Off for the demo,
# so an outbound conversation can be shown in the evening.
ENFORCE_CONTACT_HOURS = False

# --- Use cases ---
# Folder names under modules/ that are switched on.
ENABLED_MODULES = ["payments", "renewal"]

# --- Loans ---
# ASSUMPTION: the size of the bank's discount for paying a weekly payment on
# time is not known. The seed data uses it to derive the on-time payment
# from the standard one.
ON_TIME_DISCOUNT_PERCENT = 10

# --- Payment assistant module ---
# ASSUMPTION: the bank may send a payment reminder this many days before the
# due date.
REMINDER_DAYS_BEFORE_DUE = 2
# ASSUMPTION, informational only: nothing enforces it, because the demo
# starts one conversation at a time.
MAX_REMINDERS_PER_WEEK = 2
# ASSUMPTION, and a proposed change: a payment promise must be dated at most
# this many days from today. The bank's phone promise today is same-day.
PROMISE_MAX_DAYS = 15
# ASSUMPTION, no number to set: a promise must be for at least one on-time
# weekly payment and at most the total overdue. A customer who is not late
# yet may promise a date after the due date, for one weekly payment.

# ASSUMPTION: broken promises a customer may have and still make a new one
# here. 1 means: one new promise after a broken one, then a person takes over.
MAX_BROKEN_PROMISES = 1

# bank doc, no number to set: under the catch-up program the customer pays
# the missed weekly payments and the coming one at the on-time price. What
# is waived is the rest of what they would owe by the pay-by date: the late
# interest and the on-time discounts they had lost. Once per loan, and not
# for a loan that is already restructured, renewed or on a plan.

REGULARIZATION_NAME = "Ponte al corriente"   # bank doc: the program's name
REGULARIZATION_MIN_MISSED = 2                # bank doc: from 2 missed payments...
REGULARIZATION_MAX_MISSED = 22               # bank doc: ...up to 22
# ASSUMPTION: the program's pay-by date is this many days from today. The
# plan does not say how the bank sets it.
REGULARIZATION_PAY_WITHIN_DAYS = 7
# bank doc: said to the customer when they will pay under the program.
REGULARIZATION_CASHIER_INSTRUCTION = (
    'Al pagar en ventanilla, diga al cajero que su pago es para el programa '
    '"Ponte al corriente".'
)
# bank doc: where customers can pay.
PAYMENT_CHANNELS = [
    "App Banco Azteca",
    "Ventanilla en sucursal Banco Azteca",
    "Transferencia SPEI",
    "Cobrador de Banco Azteca",
]

# --- Renewal module (ALL ASSUMPTIONS, placeholders for real policy) ---
# ASSUMPTION, no number to set: a customer who is late or has an active
# payment promise is never offered, quoted or started on a loan.

# ASSUMPTION, no number to set: only a customer with a pre-approved limit on
# record can be offered a loan. The limits are in the seed data.

# ASSUMPTION, no number to set: the quote is equal weekly payments at the
# published annual rate divided by 52, without IVA. It is an estimate, and
# the customer is told so.

# A customer may be offered a new loan only if all four of these hold:
RENEWAL_MIN_ON_TIME_PERCENT = 90   # at least this share of payments made on time
RENEWAL_NO_LATE_WEEKS = 8          # no late payment in this many weeks
RENEWAL_NO_PROMISE_MONTHS = 6      # no payment promise, kept or not, in this many months
RENEWAL_MIN_REPAID_PERCENT = 75    # at least this share of the current loan's payments made
RENEWAL_MIN_AMOUNT = 2000          # the smallest new loan, in pesos
RENEWAL_TERMS_WEEKS = [26, 39, 52]  # the terms on offer, in weeks
# The product whose published rate and CAT are quoted for the new loan.
RENEWAL_PRODUCT = "Préstamo personal"
# After an offer is declined or an application is started, the bank does not
# offer again for this many days.
RENEWAL_REOFFER_DAYS = 30
# Shown to the customer when an application is started.
RENEWAL_APPLICATION_STATUS = "iniciada, pendiente de confirmación en la app"

# --- Published figures (bank doc) ---
# SOURCE NEEDED: the address of Banco Azteca's "Ponte al corriente" terms
# page, the source of every "bank doc" value in this file. Claude could not
# open the page to check any of them.
PUBLISHED_RATES_SOURCE_URL = ""
# Annual interest rate and average CAT per product, in percent, without IVA.
# The renewal quote reads them.
PUBLISHED_RATES = {
    "Préstamo personal": {"annual_rate": 49.62, "cat": 83.5},
    "Crédito de consumo": {"annual_rate": 40.53, "cat": 63.5},
}

# --- Demo guardrails ---
# Maximum customer messages per browser session, to cap API spend on a
# public link.
MAX_TURNS_PER_SESSION = 40

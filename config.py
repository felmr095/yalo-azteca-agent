"""Every tunable number and name lives here.

Unless a value is marked "bank doc", nothing in this file is a confirmed
Banco Azteca fact. Each value is an ASSUMPTION made for the demo, to be
replaced once the real policy is known. Use-case modules add their own
policy numbers below the core section.
"""

# --- Identity of the agent (shown to the customer, used in the rulebook) ---
BANK_NAME = "Banco Azteca"
AGENT_NAME = "Azul"  # ASSUMPTION: placeholder persona name

# --- Model ---
MODEL = "claude-opus-5-5"
# How hard the model thinks before answering: "low", "medium" or "high".
# Lower is faster and cheaper; raise it if the agent starts missing rules.
EFFORT = "medium"
MAX_TOKENS = 16000
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
MAX_VERIFICATION_ATTEMPTS = 3

# --- Outbound contact (ASSUMPTIONS) ---
# The bank only starts a conversation from CONTACT_HOUR_START:00 up to, but
# not including, CONTACT_HOUR_END:00.
CONTACT_HOUR_START = 7
CONTACT_HOUR_END = 21
# The hours are always stated in the rulebook. Set this to True to also
# refuse, in code, to start a conversation outside them. Off for the demo,
# so an outbound conversation can be shown in the evening.
ENFORCE_CONTACT_HOURS = False

# --- Use cases ---
# Folder names under modules/ that are switched on.
ENABLED_MODULES = ["payments"]

# --- Loans ---
# ASSUMPTION: the size of the bank's discount for paying a weekly payment on
# time is not known. The seed data uses it to derive the on-time payment
# from the standard one.
ON_TIME_DISCOUNT_PERCENT = 10

# --- Payment assistant module ---
# Each value is marked "bank doc" (taken from the bank's published terms, as
# reported in the plan; Claude has not seen the pages) or ASSUMPTION.
#
# ASSUMPTION: the bank may send a payment reminder this many days before the
# due date.
REMINDER_DAYS_BEFORE_DUE = 2
# ASSUMPTION, informational only: nothing enforces it, because the demo
# starts one conversation at a time.
MAX_REMINDERS_PER_WEEK = 2
# ASSUMPTION, and a proposed change: a payment promise must be dated at most
# this many days from today. The bank's phone promise today is same-day.
PROMISE_MAX_DAYS = 15
# A promise must be for at least one on-time weekly payment and at most the
# total overdue. No number to set here.
# ASSUMPTION: broken promises a customer may have and still make a new one
# here. 1 means: one new promise after a broken one, then a person takes over.
MAX_BROKEN_PROMISES = 1

# The catch-up program. The customer pays the missed weekly payments and the
# coming one at the on-time price. What is waived is the rest of what they
# would owe by the pay-by date: the late interest and the on-time discounts
# they had lost. Once per loan, and not for a loan that is already
# restructured, renewed or on a plan.
REGULARIZATION_NAME = "Ponte al corriente"   # bank doc
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

# --- Published figures (bank doc) ---
# Annual interest rate and average CAT per product, in percent, without IVA.
# Not used by the payment assistant; the renewal quote will read them.
# SOURCE NEEDED: Banco Azteca's "Ponte al corriente" terms page, which is
# also the source of every "bank doc" value above. Paste its address here.
# Claude could not open the page to check any of them.
PUBLISHED_RATES_SOURCE_URL = ""
PUBLISHED_RATES = {
    "Préstamo personal": {"annual_rate": 49.62, "cat": 83.5},
    "Crédito de consumo": {"annual_rate": 40.53, "cat": 63.5},
}

# --- Demo guardrails ---
# Maximum customer messages per browser session, to cap API spend on a
# public link.
MAX_TURNS_PER_SESSION = 40

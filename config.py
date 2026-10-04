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

# --- Payment assistant module (ALL ASSUMPTIONS, placeholders for real policy) ---
# The bank may send a payment reminder this many days before the due date.
REMINDER_DAYS_BEFORE_DUE = 5
# Late interest charged per day on the overdue amount, in percent.
LATE_INTEREST_DAILY_PERCENT = 0.2
# A payment promise must be dated at most this many days from today. The
# bank does not do this today: its phone promise is for the same day.
PROMISE_MAX_DAYS = 15
# A promise must be for at least one weekly payment and at most the total
# overdue (overdue payments plus late interest). No number to set here.
# Broken promises a customer may have and still make a new commitment here.
# 1 means: one new commitment after a broken one, then a person takes over.
MAX_BROKEN_PROMISES = 1
# The catch-up offer: pay everything overdue by an agreed date and part of
# the late interest is waived. One use per loan.
REGULARIZATION_NAME = "Ponte al corriente"
REGULARIZATION_MIN_DAYS_LATE = 7    # offered from this many days late...
REGULARIZATION_MAX_DAYS_LATE = 60   # ...up to this many; later, a person decides
REGULARIZATION_WAIVER_PERCENT = 50  # share of the late interest waived
REGULARIZATION_MAX_DAYS = 7         # the customer must pay within this many days
# Where customers can pay, and how. Quoted to the customer in Spanish.
PAYMENT_CHANNELS = {
    "App Banco Azteca": "en la opción de pagos de la app",
    "Ventanilla": "en cualquier sucursal Banco Azteca, con identificación oficial",
    "Transferencia SPEI": "con la CLABE que aparece en la app",
    "Cobrador": "con el cobrador de Banco Azteca que ya le atiende; pida siempre su comprobante",
}

# --- Published figures (bank doc) ---
# Annual interest rate and average CAT per product, in percent, without IVA.
# Not used by the payment assistant; the renewal quote will read them.
# SOURCE NEEDED: Banco Azteca's "Ponte al corriente" terms page. Paste its
# address here. Claude could not open the page to check the figures.
PUBLISHED_RATES_SOURCE_URL = ""
PUBLISHED_RATES = {
    "Préstamo personal": {"annual_rate": 49.62, "cat": 83.5},
    "Crédito de consumo": {"annual_rate": 40.53, "cat": 63.5},
}

# --- Demo guardrails ---
# Maximum customer messages per browser session, to cap API spend on a
# public link.
MAX_TURNS_PER_SESSION = 40

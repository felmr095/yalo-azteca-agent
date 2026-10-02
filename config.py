"""Every tunable number and name lives here.

Nothing in this file is a confirmed Banco Azteca fact. Each value is an
ASSUMPTION made for the demo, to be replaced once the real policy is known.
Use-case modules add their own policy numbers below the core section.
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
# None means "use the real date". Tests set a fixed date ("2026-10-02") so
# that "late" and "within N days" give the same answer on every run.
FIXED_TODAY = None

# --- Identity verification (ASSUMPTIONS) ---
MAX_VERIFICATION_ATTEMPTS = 3

# --- Demo guardrails ---
# Maximum customer messages per browser session, to cap API spend on a
# public link.
MAX_TURNS_PER_SESSION = 40

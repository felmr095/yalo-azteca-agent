# Build status brief: Banco Azteca agent (Yalo take-home)

*Status as of 2026-10-03.*

## Purpose of this brief

Evaluate where the working demo stands, what is missing, and how to adapt the remaining build plan to the use cases now selected. The build was designed so that use cases can be swapped in late, so selecting different ones from the placeholders is expected.

## Context

- **Deliverable:** a working customer-facing agent for Banco Azteca that runs at least two use cases end to end, shown live.
- **Timeline:** about 4 days, with work starting 2026-10-02.
- **Design goal:** a reusable scaffold that any banking use case plugs into. The first module (collections) exists to prove the pattern and is considered throwaway.

## Stack

| Layer | Choice |
|---|---|
| Language | Python |
| Model | Claude API (`claude-opus-5-5`), called through a hand-written tool loop with no agent framework |
| Data | SQLite mock bank; each chat session gets its own fresh copy |
| Interface | Streamlit chat screen, plus a terminal chat |
| Languages | Customer-facing Mexican Spanish ("usted"); code in English |

## Done and verified

Milestones 1–3 of 5 are complete and committed to git.

**Shared core (used by every use case):**

- **Rulebook:** an editable plain-text rule file shared by all use cases (role, tone, identity, compliance, handoff triggers), plus one rule file per use case. Policy numbers are filled in from the config file, so the rules and the code cannot disagree.
- **Tool layer:** every tool call passes one checkpoint that enforces rules in code. Data is locked until identity is verified. No actions are allowed after a handoff. Undeclared inputs are rejected. Refusals go back to the model as readable reasons it can recover from.
- **Identity:** the customer is fixed by the phone number the chat comes from, so the model cannot name or look up anyone else. Verification is date of birth plus the last 4 digits of the account number, with 3 attempts and then a lockout.
- **Shared tools:** `verify_identity`, `get_customer_profile`, `handoff_to_human` (creates a ticket with a reason and a Spanish summary).
- **Logging:** every message, tool call and result is saved with timestamps, and can be downloaded from the chat screen.
- **Config file:** every policy number, each labelled as an assumption.
- **Outbound openings:** the agent can write first on behalf of a use case. Before verification it is told only the reason for the contact and the account holder's name.
- **Demo screen:** a picker for which customer the chat comes from, a choice of who writes first, a live view of verification and handoff state, a "what the agent did" panel under each reply, a reset button, a passcode, and a cap of 40 messages per session.

**Mock data:** six fictional customers. One is current on a loan, three are late (by 5, 12 and 30 days), one has a loan and two broken promises, and one has savings only.

**Collections module (thin):**

- **Tools:** loan status, register a payment promise, update contact phone.
- **Policies enforced in code (all placeholders):**
  - promise dated within 15 days;
  - at least 50% of the overdue amount;
  - only one active promise at a time;
  - one new promise allowed after a broken one, then handoff.

**Tests:**

- **Policy tests:** 26 tests that call the tools directly with no model involved. They are instant, free and all pass.
- **Scripted conversations:** 6 conversations played against the live model, checked on what the agent did (tool calls and database rows) rather than its wording. All passed in one run of about 1 min 40 s. They cover:
  - the happy path;
  - a third party who learns nothing;
  - a duplicate promise being blocked;
  - a customer with two broken promises being handed off;
  - an out-of-range date being renegotiated;
  - a verification lockout ending in handoff.

**Performance:** replies take about 5–7 seconds at medium effort.

## Cost of adding a use case

A use case is one folder containing six files: a module definition, a rule file, its tools, its own tables and fake data, its policy tests and its scripted conversations. Its policy numbers go in the config file, and it is switched on by name. No core changes are needed if the use case fits the constraints below.

The core currently supports:

- one agent with the tools of every enabled module loaded at once;
- text chat only;
- core data limited to customers, accounts, loans, payments and handoff tickets (anything else, such as cards, transactions, remittances or applications, becomes a table in the module);
- one identity method for every use case.

Cheap to build:

- tools that read or write mock data;
- business rules enforced in code;
- inbound or outbound conversation starts;
- handoffs;
- scripted tests.

Expensive, or would need core changes:

- document or image upload (e.g. ID checks for onboarding);
- voice;
- WhatsApp-style buttons or rich messages;
- different identity strength per action (e.g. a step-up check before changing a phone number);
- scheduled or batch outbound campaigns (outbound is currently simulated one conversation at a time);
- live external data;
- a cross-conversation metrics dashboard.

## Not done

| Item | Status |
|---|---|
| Deployment | Not yet live. The code is committed locally only. It needs the user's GitHub account, then Streamlit Community Cloud. This is the main delivery risk; it should happen early. |
| Second use case (milestone 4) | Not started. The placeholder was a thin inbound account-support module, pending use-case selection. |
| Demo layer (milestone 5) | Not started: an outcome summary for the "where agents move numbers" story, a rehearsed demo script, and a backup recording. |
| Reply speed | Optional; not measured. Lower effort or streaming replies could help. |

## Open decisions (owner: the user)

- **Security:** rotate the API key (it was exposed in a session log) and set a spend limit before the public link goes live.
- **Agent details:** reply speed versus thoroughness; persona name (placeholder "Azul"); identity factors.
- **Compliance rules:** these are generic and should be checked against the regulations that actually apply in Mexico.
- **Use cases:** the final choice; the second use case; whether "update phone number" should stay in scope, since it is an account-takeover risk.
- **Collections placeholders:** the policy numbers; the payment channels quoted to customers; whether the outbound opening should use the customer's full name before verification.
- **Demo:** the demo script and backup; the agent not knowing the time of day.

## What I need back

1. **For each selected use case:**
   - inbound or outbound;
   - its tools, as verbs on data;
   - its policy rules with placeholder numbers;
   - which seed customers and data it needs;
   - its handoff triggers;
   - 3–5 scripted test conversations (the happy path plus the edge cases that matter for the pitch);
   - the business metric it moves, and how the demo would show it.
2. **Fit check:** whether any selected use case falls into the "expensive" list above. If so, propose a reduced version or name the core change needed.
3. **Collections:** keep, cut, or reshape it.
4. **Revised plan:** remaining milestones in priority order for the time left, with deployment and a working demo protected first.
5. **Decisions:** which open decisions the research has already settled.

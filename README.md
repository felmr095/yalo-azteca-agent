# Banco Azteca customer agent

A chat agent for Banco Azteca customers, built as a take-home for Yalo. It
runs two use cases end to end:

- **Payment assistant:** reminds a customer of a payment that is coming up,
  and helps a customer who is behind to catch up, with the bank's "Ponte al
  corriente" program or a payment promise.
- **Loan renewal:** offers a new loan to a customer with a good payment
  record, quotes it, and starts the application.

The customers, their loans and most policy numbers are invented for the
demo. Every number is in `config.py`, marked either "bank doc" or
"ASSUMPTION".

## Try it

**https://yalo-azteca-agent.streamlit.app**

The app asks for a passcode. It was sent to you together with this link; it
is not in this repository. If the app shows a "waking up" screen, give it
half a minute.

The agent answers in Mexican Spanish. The controls around the chat are in
English: they are for the person running the demo, not for the customer.

## A 5-minute test

Two conversations, about two minutes each. Each step below names the
combination to use in the sidebar: the **customer** ("Chat is coming from")
and the **start** ("Conversation starts with"). Picking a customer sets the
start that suits their story; you can change it. Type the phrases exactly,
or in your own words: the agent's wording changes from run to run, but the
amounts and what it does should not.

Nothing is sent to the model until you ask for it. When the bank is to
write first, press **Start conversation**; when the customer writes first,
the conversation starts with your first message.

### 1. A customer in hardship

**Customer: Miguel Ángel Sánchez Cruz · Start: Bank reaches out: payments**

He has missed 5 weekly payments. The bank writes to him, and he says he has
lost his job.

1. Choose Miguel Ángel; the start sets itself. Press **Start
   conversation** and the agent writes first. It asks for him by first
   name and says only that it is about "un asunto de su cuenta".
2. Type: `Sí, soy yo`
3. Type: `Nací el 30 de enero de 1984 y mi cuenta termina en 4567`
   The agent now explains the loan: 5 payments missed and $3,186.00 pesos
   overdue.
4. Type: `Me quedé sin trabajo hace un mes y ahorita no tengo cómo pagar nada`

What to check: the agent asks him for nothing more and passes him to a
person. Under its reply, "What the agent did" shows the handoff with a
summary written for the human agent. In the sidebar, "Outcome" shows
`Handoff: ticket HT-0001, reason hardship` and `Promise: none`.

**The other path, same customer and start.** Press "Reset conversation and
data", then "Start conversation", repeat steps 2 and 3, and type `¿Qué
opciones tengo?` instead. The
agent explains "Ponte al corriente": he owes $3,786.00, $546.00 is waived,
and he pays $3,240.00 by a date about a week out.

### 2. A renewal quote

**Customer: Carmen Beatriz Ortiz Navarro · Start: Bank reaches out: renewal**

She has made 45 of her 52 payments, all on time, and is pre-approved for a
new loan of up to $8,000.00 pesos.

1. Choose Carmen Beatriz; the start sets itself. Press **Start
   conversation** and the agent writes first.
2. Type: `Sí, soy yo`
3. Type: `Nací el 11 de abril de 1982 y mi cuenta termina en 9012`
   The agent tells her about the offer: $2,000.00 to $8,000.00, over 26, 39
   or 52 weeks.
4. Type: `¿Cuánto pagaría por semana si pido 5,000?`
   The agent asks over how many weeks.
5. Type: `A 52 semanas`
   The agent quotes $122.42 a week, $6,365.84 in total, and a CAT of 83.5%.
6. Type: `Sí, quiero ese`

What to check: the agent gave the weekly payment, the total and the CAT
before asking whether to go ahead. It then gives a reference and sends her
to the app to confirm; it never says the money is on its way. In the
sidebar, "Outcome" shows the quote and the application.

### Three customers the bank may not write to

For these three, pressing **Start conversation** leaves the chat empty and
one line above it says why. That is the rule working, not a fault: the
check runs in code, and the model is never called.

| Customer · Start | Why the bank does not write |
|---|---|
| Ana Karen · Bank reaches out: payments | She has an active payment promise; the hold suppresses contact until its date, a few days out. |
| Ricardo Daniel · Bank reaches out: payments | The same: an active promise and its hold. |
| Sofía Alejandra · Bank reaches out: renewal | She declined a loan offer 10 days ago; no new offer for 20 more days. |

Switch the start to "Customer writes first" to chat as any of them. Ask
Ana Karen's agent for a second promise, or Ricardo Daniel's for more
credit: both are refused.

### Things worth trying after that

- **José Luis Ramírez Torres · Bank reaches out: payments.** Answer as
  someone else (`No, él no está. Soy su hermano, ¿de qué se trata?`): the
  agent says nothing about the loan.
- **Any customer.** Give a wrong date of birth three times: verification
  locks and the conversation goes to a person.
- **Carmen Beatriz · Bank reaches out: renewal.** Ask for `15,000 pesos`:
  the agent explains her limit.
- **Unknown number · Customer writes first.** Ask `¿dónde puedo pagar un
  préstamo?`: answered without verification, and nothing else is.

## Seed customers

Pick one in the sidebar under "Chat is coming from". To verify, give the
date of birth and the last 4 digits of the account. All are fictional.
"Bank first" means "Bank reaches out: ..." under "Conversation starts
with"; picking a customer selects the start shown first in their row. Every
date in the data is set relative to today, so "due in 2 days" is always
true.

| Customer | Situation | Born | Last 4 | What to demo |
|---|---|---|---|---|
| María Guadalupe | Up to date; payment due in 2 days | 14 March 1988 | 1234 | Bank first (payments): a reminder. Say you will pay in the app and nothing is recorded; say you can only pay a few days later and a promise with a hold is. |
| Laura Patricia | 1 payment missed | 5 December 1993 | 7890 | Bank first (payments). Ask for "Ponte al corriente": not available yet, a promise is offered instead. |
| José Luis | 2 payments missed | 2 November 1979 | 2345 | Bank first (payments): the "Ponte al corriente" offer (owes $914.40, pays $810.00). Also: answer as a relative; say "ya pagué ayer"; ask to drop the interest; ask to change a phone number. |
| Miguel Ángel | 5 payments missed; one broken promise | 30 January 1984 | 4567 | Bank first (payments): say you lost your job and you are handed to a person. Or ask what your options are: the full offer (owes $3,786.00, pays $3,240.00) and the instruction for the cashier. |
| Juan Carlos | 3 payments missed; two broken promises | 17 May 1991 | 6789 | Bank first (payments). Any promise is refused and handed to a person. |
| Luis Fernando | 3 payments missed; loan already on a plan | 23 August 1975 | 8901 | Bank first (payments). Ask for "Ponte al corriente": excluded, a promise only. |
| Ana Karen | 1 payment missed; has an active promise due in 3 days | 21 July 1995 | 3456 | Bank first (payments) is refused: the promise puts collections on hold. Customer first, asking for a second promise: refused. |
| Carmen Beatriz | 45 of 52 payments made, all on time; pre-approved for $8,000.00 | 11 April 1982 | 9012 | Bank first (renewal): ask what $5,000.00 over 52 weeks costs, accept, and an application starts. Or decline; or ask for $15,000.00; or say paying is hard. |
| Ricardo Daniel | Good record, but an active promise due in 3 days | 27 February 1990 | 0123 | Bank first (payments) is refused by the hold, and bank first (renewal) because of the promise. Customer first, asking for more credit: none is offered. |
| Sofía Alejandra | Pre-approved for $5,000.00; declined 10 days ago | 19 October 1986 | 1357 | Bank first (renewal) is refused for 30 days after a decline. Customer first: she can still ask for a loan herself. |
| Rosa Elena | Savings only, no loan | 8 September 1967 | 5678 | Customer first: a balance question. Bank first is refused for both use cases. |
| Unknown number | Not a customer | none | none | Customer first: ask where a loan can be paid. It is answered without verification; nothing else is. |

## Run it locally

Needs Python 3.9 or later and an Anthropic API key.

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml

Put your API key and a passcode of your choice in `.streamlit/secrets.toml`
(the file is ignored by git), then:

    streamlit run app.py     # the chat screen, at http://localhost:8501
    python chat_cli.py       # the same chat in the terminal

## Tests

    python -m tests.run          # policy tests: instant, free, no model
    python -m tests.run --live   # plus scripted conversations (about 2 min)
    python -m tests.run --live --only "renewal: offer"   # only matching ones

- **Policy tests** call the tools directly and prove that the rules hold in
  code whatever the model says: identity, limits on promises and loans, who
  may be contacted or offered credit.
- **Scripted conversations** play a customer against the real model and
  check what the agent did (tool calls and database rows), not how it
  phrased things. They cost API credit: after a change, re-run only the
  ones it affects, with `--only` and part of their name.

Transcripts of the scripted conversations are saved in `logs/tests/`.

## Reading a conversation log

Every conversation is logged, and the chat screen has a button to download
the log. To read one as a chat:

    python -m tools.transcript logs/<file>.jsonl

It prints who said what, with what the agent did in square brackets, for
example `[verify_identity(...) -> ok: ...]`. Add `--full` to see complete
tool results.

## What is real and what is assumed

`ASSUMPTIONS.md` lists every setting of the agent with its value and where
it comes from. It is generated from `config.py`, so it cannot drift from
what the code enforces:

    python -m tools.assumptions --write

- **Bank doc:** the "Ponte al corriente" rules (2 to 22 missed payments, not
  for a loan on a plan), the payment channels, the cashier instruction, and
  the published rates and CAT. These come from the bank's published terms
  and conditions, linked in `ASSUMPTIONS.md`.
- **Assumption:** everything else about policy, including the size of the
  on-time discount, the 15-day promise window, that the program is once
  per loan, the renewal criteria and the quote formula.
- **Invented:** the customers, their loans and their histories.

`DECISIONS.md` records each decision, when it was made and why.

## How AI tools were used

- **Claude in the Claude app:** the research, the analysis of the bank,
  the business case, and the drafts of the roadmap, the judgment and the
  run plan.
- **Claude Code** (Anthropic's coding agent): the agent, the tests, this
  README and the deployment.
- **Whisper, via Groq:** transcribing interviews.
- **The agent itself** is Claude (`claude-opus-5-5`), called through the
  Anthropic API.

I chose the use cases, the policies and the order of work; wrote the
executive summary, the ordering and the judgment; reviewed each stage;
tested the live app on my phone; and approved every merge. `DECISIONS.md`
is the record of those decisions.

Two limits worth knowing:

- **The bank's figures were checked against one document.** They came from
  the research done in the Claude app. On 4 October 2026 Claude Code read
  them against the bank's "Ponte al corriente" terms and conditions, linked
  in `ASSUMPTIONS.md`, and the values marked "bank doc" match it. The one
  thing that document does not support is that the program can be used
  only once per loan, so that rule is marked as an assumption.
- **The tests guard against the model's mistakes.** Policy rules are
  enforced in code and tested without the model. The scripted
  conversations run against the real model, but what they check is what
  the agent did, not what it said.

## How it is built

The model is Claude, called through a hand-written tool loop with no agent
framework. The rules the agent must follow are in two places:

- **The rulebook** (plain text) tells the model how to behave.
- **The tools** (code) enforce the rules that must never break. Data is
  locked until identity is verified, nothing happens after a handoff, and
  every policy limit is checked in the tool, so a persuasive customer
  cannot talk the agent past it.

Each use case is a folder under `modules/` that plugs into a shared core.

| To change...                         | Edit...                             |
|--------------------------------------|-------------------------------------|
| Rules for every use case             | `rulebook/shared.md`                |
| Rules for one use case               | `modules/<name>/rulebook.md`        |
| Policy numbers, model, agent name    | `config.py`                         |
| The fake customers                   | `data/seed.py`                      |
| A use case's own fake data           | `modules/<name>/seed.py`            |

Rulebook and config changes apply on the next message. Seed changes apply
after pressing "Reset conversation and data" in the sidebar.

| File                    | What it does                                             |
|-------------------------|----------------------------------------------------------|
| `app.py`                | The chat screen (Streamlit).                             |
| `chat_cli.py`           | The same chat in the terminal, with tool calls printed.  |
| `config.py`             | Every tunable value, each labelled.                      |
| `rulebook/shared.md`    | Rules that apply to every use case.                      |
| `core/conversation.py`  | Wires one conversation together; the single entry point. |
| `core/agent.py`         | The loop that talks to Claude and runs tools.            |
| `core/tools.py`         | The tool layer: checks every tool call must pass.        |
| `core/core_tools.py`    | Shared tools: verify identity, profile, hand off.        |
| `core/session.py`       | Who the chat is with and whether they are verified.      |
| `core/logger.py`        | Writes every event to `logs/<session>.jsonl`.            |
| `core/rulebook.py`      | Assembles the rulebook and fills in config values.       |
| `core/db.py`            | The mock bank's core tables.                             |
| `core/clock.py`         | Today's date and the time, in Mexico City time.          |
| `core/modules.py`       | The contract a use case must satisfy to plug in.         |
| `data/seed.py`          | Fake customers; `python -m data.seed` writes `bank.db`.  |
| `modules/payments/`     | The payment assistant use case.                          |
| `modules/renewal/`      | The loan renewal use case.                               |
| `tests/run.py`          | The test runner.                                         |
| `tools/transcript.py`   | Prints a conversation log as a readable chat.            |
| `tools/assumptions.py`  | Generates `ASSUMPTIONS.md` from `config.py`.             |
| `ASSUMPTIONS.md`        | Every setting, its value and where it comes from.        |
| `DECISIONS.md`          | Open and settled decisions, with the reasons.            |

### Adding a use case

A use case is a folder under `modules/`. Copy `modules/payments/` as a
template. It contains:

| File                    | What it holds                                            |
|-------------------------|----------------------------------------------------------|
| `__init__.py`           | `MODULE`: the name, tools, rulebook and outbound rules.  |
| `rulebook.md`           | This use case's rules, in plain text.                    |
| `tools.py`              | Its tools, with policy enforced in code.                 |
| `seed.py`               | Its own tables and fake data.                            |
| `test_policy.py`        | Rule checks that run without the model.                  |
| `test_conversations.py` | Scripted conversations against the real model.           |

Then add the folder name to `ENABLED_MODULES` and its policy numbers to
`config.py`. Nothing under `core/` needs to change.

## Deployment

The live app runs on Streamlit Community Cloud, from the `main` branch of
https://github.com/felmr095/yalo-azteca-agent, on Python 3.12.

- **To update it:** push to `main`. Streamlit Cloud redeploys by itself
  within a minute or two.
- **Secrets:** `ANTHROPIC_API_KEY` and `APP_PASSCODE` are set in the
  Streamlit dashboard (the app's Settings > Secrets). They are not in the
  repository. To change one, edit it there; the app restarts.

The app goes to sleep after a period without visitors; open it a few
minutes before a demo to wake it up.

To deploy a fresh copy: at https://share.streamlit.io choose "Create app",
pick the repository, the `main` branch and `app.py`. Under "Advanced
settings" choose Python 3.12 and paste the two lines from `secrets.toml`
into the Secrets box.

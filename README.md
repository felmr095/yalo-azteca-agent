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

Two conversations, about two minutes each. The sidebar on the left chooses
who the chat comes from and who writes first. Type the phrases exactly, or
in your own words; the agent's wording changes from run to run, but the
amounts and what it does should not.

### 1. A customer in hardship (Miguel Ángel)

He has missed 5 weekly payments. The bank writes to him, and he says he has
lost his job.

1. In the sidebar, set "Chat is coming from" to **Miguel Ángel Sánchez
   Cruz** and "Conversation starts with" to **Bank reaches out: payments**.
   The agent writes first. It asks for him by first name and says only
   that it is about "un asunto de su cuenta".
2. Type: `Sí, soy yo`
3. Type: `Nací el 30 de enero de 1984 y mi cuenta termina en 4567`
   The agent now explains the loan: 5 payments missed and $3,186.00 pesos
   overdue.
4. Type: `Me quedé sin trabajo hace un mes y ahorita no tengo cómo pagar nada`

What to check: the agent asks him for nothing more and passes him to a
person. Under its reply, "What the agent did" shows the handoff with a
summary written for the human agent. In the sidebar, "Outcome" shows
`Handoff: ticket HT-0001, reason hardship` and `Promise: none`.

To see the other path, press "Reset conversation and data", repeat steps 2
and 3, and type `¿Qué opciones tengo?` instead. The agent explains "Ponte
al corriente": he owes $3,786.00, $546.00 is waived, he pays $3,240.00.

### 2. A renewal quote (Carmen Beatriz)

She has made 45 of her 52 payments, all on time, and is pre-approved for a
new loan of up to $8,000.00 pesos.

1. In the sidebar, choose **Carmen Beatriz Ortiz Navarro** and **Bank
   reaches out: renewal**.
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

### Things worth trying after that

- Answer as someone else (`No, él no está. Soy su hermano, ¿de qué se
  trata?`) with José Luis: the agent says nothing about the loan.
- Give a wrong date of birth three times: verification locks and the
  conversation goes to a person.
- Ask Carmen Beatriz for `15,000 pesos`: the agent explains her limit.
- Choose Ana Karen with "Bank reaches out: payments": the bank is not
  allowed to contact her, because her payment promise puts collections on
  hold.

## Seed customers

Pick one in the sidebar under "Chat is coming from". To verify, give the
date of birth and the last 4 digits of the account. All are fictional.
"Bank first" means choosing "Bank reaches out: ..." under "Conversation
starts with".

| Customer | Situation | Born | Last 4 | What to demo |
|---|---|---|---|---|
| María Guadalupe | Up to date; payment due in 2 days | 14 March 1988 | 1234 | Bank first (payments): a reminder. Say you will pay in the app and nothing is recorded; say you can only pay a few days later and a promise with a hold is. |
| Laura Patricia | 1 payment missed | 5 December 1993 | 7890 | Bank first (payments). Ask for "Ponte al corriente": not available yet, a promise is offered instead. |
| José Luis | 2 payments missed | 2 November 1979 | 2345 | Bank first (payments): the "Ponte al corriente" offer (owes $914.40, pays $810.00). Also: answer as a relative; say "ya pagué ayer"; ask to drop the interest; ask to change a phone number. |
| Miguel Ángel | 5 payments missed; one broken promise | 30 January 1984 | 4567 | Customer first, asking to catch up: the full offer (owes $3,786.00, pays $3,240.00) and the instruction for the cashier. Or say you lost your job: handed to a person. |
| Juan Carlos | 3 payments missed; two broken promises | 17 May 1991 | 6789 | Bank first (payments). Any promise is refused and handed to a person. |
| Luis Fernando | 3 payments missed; loan already on a plan | 23 August 1975 | 8901 | Customer first, asking for "Ponte al corriente": excluded, a promise only. |
| Ana Karen | 1 payment missed; has an active promise | 21 July 1995 | 3456 | Bank first (payments) is blocked by the collections hold. Customer first, asking for a second promise: refused. |
| Carmen Beatriz | 45 of 52 payments made, all on time; pre-approved for $8,000.00 | 11 April 1982 | 9012 | Bank first (renewal): ask what $5,000.00 over 52 weeks costs, accept, and an application starts. Or decline; or ask for $15,000.00; or say paying is hard. |
| Ricardo Daniel | Good record, but an active promise | 27 February 1990 | 0123 | Customer first, asking for more credit: none is offered. Bank first (renewal) is blocked. |
| Sofía Alejandra | Pre-approved for $5,000.00; declined 10 days ago | 19 October 1986 | 1357 | Bank first (renewal) is blocked for 30 days after a decline. She can still ask for a loan herself. |
| Rosa Elena | Savings only, no loan | 8 September 1967 | 5678 | Bank first is blocked for both use cases. Customer first: a balance question. |
| Unknown number | Not a customer | none | none | Ask where a loan can be paid: answered without verification. Nothing else is. |

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

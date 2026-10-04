# Banco Azteca agent scaffold

A customer-facing banking agent built for a Yalo take-home. The core is
use-case-agnostic; each use case plugs in as a module. All customers,
figures and policies are fictional placeholders.

## Run it locally

1. Open a terminal in this folder and activate the Python environment:

       source .venv/bin/activate

   (First time on a new machine: `python3 -m venv .venv`, activate it, then
   `pip install -r requirements.txt`.)

2. Give it an API key. Copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and paste your key from
   https://console.anthropic.com. Set a spend limit on that key.

3. Start the chat screen:

       streamlit run app.py

To chat in the terminal instead, the key must be an environment variable:

    export ANTHROPIC_API_KEY="sk-ant-..."
    python chat_cli.py

## What to edit to change the agent's behaviour

| To change...                         | Edit...                             |
|--------------------------------------|-------------------------------------|
| Rules for every use case             | `rulebook/shared.md`                |
| Rules for one use case               | `modules/<name>/rulebook.md`        |
| Policy numbers, model, agent name    | `config.py`                         |
| The fake customers                   | `data/seed.py`                      |
| A use case's own fake data           | `modules/<name>/seed.py`            |

Rulebook and config changes apply on the next message. Seed changes apply
after pressing "Reset conversation and data" in the sidebar.

## Files

| File                    | What it does                                             |
|-------------------------|----------------------------------------------------------|
| `app.py`                | The chat screen (Streamlit).                             |
| `chat_cli.py`           | The same chat in the terminal, with tool calls printed.  |
| `config.py`             | Every tunable value, each labelled as an assumption.     |
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
| `data/seed.py`          | Fake customers; `python -m data.seed` writes `bank.db`.  |
| `core/modules.py`       | The contract a use case must satisfy to plug in.         |
| `modules/payments/`     | The payment assistant use case.                          |
| `modules/renewal/`      | The loan renewal use case.                               |
| `tests/run.py`          | The test runner.                                         |
| `DECISIONS.md`          | Open and settled decisions.                              |

## Adding a use case

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

## Tests

    python -m tests.run          # policy tests: instant and free
    python -m tests.run --live   # plus scripted conversations (about 2 min)
    python -m tests.run --live --only "renewal: offer"   # only matching ones

Scripted conversations cost API credit. After a change, re-run only the
ones it affects, with `--only` and part of their name.

Transcripts of the scripted conversations are saved in `logs/tests/`.


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

## Deployment

The app is live at https://yalo-azteca-agent.streamlit.app. It runs on
Streamlit Community Cloud, from the `main` branch of
https://github.com/felmr095/yalo-azteca-agent, on Python 3.12.

- **To update it:** push to `main`. Streamlit Cloud redeploys by itself
  within a minute or two.
- **Secrets:** `ANTHROPIC_API_KEY` and `APP_PASSCODE` are set in the
  Streamlit dashboard (the app's Settings > Secrets). They are not in the
  repository. To change one, edit it there; the app restarts.
- **Sharing:** send the link together with the passcode.

The app goes to sleep after a period without visitors; open it a few
minutes before a demo to wake it up.

To deploy a fresh copy: at https://share.streamlit.io choose "Create app",
pick the repository, the `main` branch and `app.py`. Under "Advanced
settings" choose Python 3.12 and paste the two lines from `secrets.toml`
into the Secrets box.

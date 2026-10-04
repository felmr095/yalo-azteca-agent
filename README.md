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
| `core/clock.py`         | "Today's date", freezable for tests.                     |
| `data/seed.py`          | Fake customers; `python -m data.seed` writes `bank.db`.  |
| `core/modules.py`       | The contract a use case must satisfy to plug in.         |
| `modules/collections/`  | The collections use case (see below).                    |
| `tests/run.py`          | The test runner.                                         |
| `DECISIONS.md`          | Open and settled decisions.                              |

## Adding a use case

A use case is a folder under `modules/`. Copy `modules/collections/` as a
template. It contains:

| File                    | What it holds                                            |
|-------------------------|----------------------------------------------------------|
| `__init__.py`           | `MODULE`: the name, tools, rulebook and outbound reason. |
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

Transcripts of the scripted conversations are saved in `logs/tests/`.

To verify as a seed customer in the chat, use the date of birth and the last
4 digits of the account number from `data/seed.py`. For the first customer:
"14 de marzo de 1988" and "1234".

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

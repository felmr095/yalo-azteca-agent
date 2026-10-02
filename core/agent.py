"""The agent loop: the one piece of code that talks to Claude.

It knows nothing about banking or about the chat screen. It is given a
rulebook, the conversation so far, and (optionally) a set of tools, and it
returns the next message for the customer. The web app, the terminal chat
and the test runner all call run_turn(), so they behave identically.

How one turn works:
  1. Send the conversation to Claude.
  2. If Claude asks to use a tool, run it, send back the result, and repeat.
  3. When Claude answers in plain text, return that text.
"""

import os
from typing import Callable, List, Optional, Tuple

import anthropic

import config

# Shown to the customer when the agent cannot produce an answer.
FALLBACK_REPLY = (
    "Disculpe, en este momento no puedo ayudarle con eso. "
    "¿Hay algo más en lo que pueda apoyarle?"
)

# A tool executor takes (tool_name, tool_input) and returns
# (result_text, is_error).
ToolExecutor = Callable[[str, dict], Tuple[str, bool]]


SECRETS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".streamlit", "secrets.toml"
)


def make_client() -> anthropic.Anthropic:
    """Uses the ANTHROPIC_API_KEY environment variable, or failing that the
    key in .streamlit/secrets.toml, so the terminal chat and tests work with
    the same setup as the web app."""
    if not os.environ.get("ANTHROPIC_API_KEY") and os.path.exists(SECRETS_FILE):
        import toml  # installed together with Streamlit

        key = toml.load(SECRETS_FILE).get("ANTHROPIC_API_KEY")
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key
    return anthropic.Anthropic()


def _call_model(client, system: str, messages: list, tools: Optional[List[dict]]):
    request = {
        "model": config.MODEL,
        "max_tokens": config.MAX_TOKENS,
        "system": system,
        "messages": messages,
        "output_config": {"effort": config.EFFORT},
    }
    if tools:
        request["tools"] = tools
    if config.REFUSAL_FALLBACK:
        return client.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request
        )
    return client.messages.create(**request)


def run_turn(
    client,
    system: str,
    messages: list,
    user_text: str,
    tools: Optional[List[dict]] = None,
    execute_tool: Optional[ToolExecutor] = None,
) -> str:
    """Add the customer's message to `messages` and return the agent's reply.

    `messages` is the full conversation in the API's format. It is updated
    in place, so the caller only has to keep hold of the same list.
    """
    messages.append({"role": "user", "content": user_text})

    for _ in range(config.MAX_TOOL_ROUNDS):
        response = _call_model(client, system, messages, tools)

        if response.stop_reason == "refusal":
            # Nothing usable came back; record the stock reply instead.
            messages.append({"role": "assistant", "content": FALLBACK_REPLY})
            return FALLBACK_REPLY

        # Keep the whole response, not just its text: it also carries the
        # model's tool requests and reasoning, which must be sent back as-is.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = "\n\n".join(b.text for b in response.content if b.type == "text")
            return text.strip() or FALLBACK_REPLY

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            content, is_error = execute_tool(block.name, block.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": results})

    return FALLBACK_REPLY

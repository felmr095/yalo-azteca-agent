"""Print a conversation log as a readable chat. Run with:

    python -m tools.transcript logs/<file>.jsonl

Each message is shown with who wrote it. What the agent did appears in
square brackets, in the order it happened: the tool, its inputs, and whether
it worked. Long tool results are cut short; add --full to see all of them.
Several files can be given at once.
"""

import json
import sys
import textwrap

WIDTH = 88
SPEAKERS = {"user_message": "Cliente:", "assistant_message": "Agente: "}
CUT = 110  # characters of a tool result shown without --full


def read(path: str) -> list:
    """The events in a log file, one per line."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _wrap(prefix: str, text: str) -> str:
    """Wrap text under a prefix, keeping the writer's own line breaks."""
    indent = " " * len(prefix)
    lines = []
    for paragraph in text.split("\n"):
        lines.append(textwrap.fill(paragraph, WIDTH, initial_indent=prefix if not lines else indent,
                                   subsequent_indent=indent) if paragraph.strip() else "")
    return "\n".join(lines)


def _cut(text: str, full: bool) -> str:
    text = " ".join(str(text).split())
    return text if full or len(text) <= CUT else text[:CUT].rstrip() + "..."


def _inputs(tool_input: dict, full: bool) -> str:
    return ", ".join(f"{name}={_cut(json.dumps(value, ensure_ascii=False), full)}"
                     for name, value in tool_input.items())


def render(events: list, full: bool = False) -> str:
    """The whole conversation as text."""
    out, pending, recorded = [], {}, []
    for e in events:
        kind = e["type"]
        if kind == "session_start":
            out.append(f"Conversation {e['session_id']}")
            out.append(f"Started {e['ts'].replace('T', ' ')} · chat from {e['phone']}"
                       + ("" if e.get("customer_id") else " (not a customer)")
                       + f" · use cases: {', '.join(e.get('modules', []))}")
        elif kind == "outbound_start":
            out.append(f"\n[the bank starts the conversation: {e['module']}]")
        elif kind == "outbound_blocked":
            out.append("\n" + _wrap("[", f"the bank did not start the conversation "
                                         f"({e['module']}): {e['reason']}]"))
        elif kind in SPEAKERS:
            out.append("\n" + _wrap(SPEAKERS[kind] + " ", e["text"]))
        elif kind == "tool_call":
            pending[e["tool"]] = e["input"]
        elif kind == "tool_result":
            call = f"{e['tool']}({_inputs(pending.pop(e['tool'], {}), full)})"
            result = ("REFUSED: " if e["is_error"] else "ok: ") + _cut(e["result"], full)
            out.append(_wrap("  [", f"{call} -> {result}]"))
        elif kind == "tool_crash":
            out.append(_wrap("  [", f"{e['tool']} crashed: {e['error']}]"))
        elif kind == "outcome":
            details = ", ".join(f"{k}={v}" for k, v in e.items()
                                if k not in ("ts", "session_id", "type", "outcome"))
            recorded.append(f"{e['outcome']} ({details})" if details else e["outcome"])
    out.append("\n" + _wrap("Recorded: ", "; ".join(recorded) if recorded else "nothing"))
    return "\n".join(out)


def main(arguments: list) -> int:
    full = "--full" in arguments
    paths = [a for a in arguments if not a.startswith("--")]
    if not paths:
        print(__doc__.strip())
        return 1
    for i, path in enumerate(paths):
        try:
            events = read(path)
        except (OSError, ValueError) as e:
            print(f"Could not read {path}: {e}")
            return 1
        print(("\n" + "=" * WIDTH + "\n\n" if i else "") + render(events, full))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

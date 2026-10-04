"""List every setting in config.py with its value, where it comes from, and
its note. Run with:

    python -m tools.assumptions            print the list
    python -m tools.assumptions --write    save it as ASSUMPTIONS.md

Each setting is one of three kinds, decided by the words in its comment, or
failing that in its section heading:

    bank doc     taken from the bank's published terms
    ASSUMPTION   made up for the demo, to be replaced by the real policy
    (neither)    a technical setting, not a claim about the bank
"""

import ast
import io
import json
import os
import re
import sys
import tokenize

ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(ROOT, "config.py")
OUTPUT_FILE = os.path.join(ROOT, "ASSUMPTIONS.md")
KINDS = ("Bank doc", "Assumption", "Setting")


def _kind(note: str, section: str) -> str:
    for text in (note.lower(), section.lower()):
        if "bank doc" in text:
            return "Bank doc"
        if "assumption" in text:
            return "Assumption"
    return "Setting"


def entries() -> list:
    """Every setting and every stand-alone rule in config.py, in order, as
    dicts with section, name (None for a rule), value, kind and note."""
    with open(CONFIG_FILE, encoding="utf-8") as f:
        source = f.read()
    lines = source.splitlines()
    comments = {}  # line number -> (column, text)
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            comments[token.start[0]] = (token.start[1], token.string.lstrip("# ").strip())
    # The values are read from the file as written, not from the running
    # program, where tests change some of them.
    settings = {}  # first line -> (name, value, last line)
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            settings[node.lineno] = (node.targets[0].id, ast.literal_eval(node.value),
                                     node.end_lineno)

    found, section, above, skip_to = [], "", [], 0

    def rule():
        """A labelled comment paragraph with no setting under it is a rule."""
        note = " ".join(above)
        if "assumption" in note.lower() or "bank doc" in note.lower():
            found.append({"section": section, "name": None, "value": None,
                          "kind": _kind(note, ""), "note": note})
        above.clear()

    for number, line in enumerate(lines, start=1):
        if number <= skip_to:
            continue
        column, text = comments.get(number, (None, ""))
        if number in settings:
            name, value, skip_to = settings[number]
            note = " ".join(above + ([text] if text else []))
            above.clear()
            if name.isupper():
                found.append({"section": section, "name": name, "value": value,
                              "kind": _kind(note, section), "note": note})
        elif column == 0 and re.fullmatch(r"-+ .* -+", text):
            rule()
            section = text.strip("- ")
        elif column == 0 and text:
            above.append(text)
        else:  # a blank line, or an empty comment line, ends a paragraph
            rule()
    return found


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def render() -> str:
    """The whole list as Markdown."""
    found = entries()
    counts = {kind: sum(e["kind"] == kind for e in found) for kind in KINDS}
    source = next(e["value"] for e in found
                  if e["name"] == "PUBLISHED_RATES_SOURCE_URL") or "not added yet"
    out = [
        "# Assumptions and sources",
        "",
        "Generated from `config.py` by `python -m tools.assumptions --write`. Do not edit",
        "this file by hand: change `config.py` and run the command again.",
        "",
        "Every setting of the agent is listed here with where it comes from:",
        "",
        f"- **Bank doc** ({counts['Bank doc']}): taken from Banco Azteca's published terms, as",
        "  reported in the project plan. They were not checked against the bank's own",
        f"  pages while this was built. Source: {source}.",
        f"- **Assumption** ({counts['Assumption']}): made up for the demo, to be replaced by the",
        "  bank's real policy.",
        f"- **Setting** ({counts['Setting']}): a technical choice, not a claim about the bank.",
        "",
        "The customers, their loans, their payment histories and their pre-approved",
        "limits are also invented; they are in `data/seed.py` and each module's",
        "`seed.py`.",
    ]
    section = None
    for e in found:
        if e["section"] != section:
            section = e["section"]
            heading = re.sub(r"\s*\((?:[^()]*(?:ASSUMPTION|bank doc)[^()]*)\)", "", section)
            out += ["", f"## {heading}", "", "| Setting | Value | Basis | Note |", "|---|---|---|---|"]
        name = f"`{e['name']}`" if e["name"] else "(a rule, no number)"
        value = f"`{json.dumps(e['value'], ensure_ascii=False)}`" if e["name"] else ""
        out.append(f"| {name} | {_cell(value)} | {e['kind']} | {_cell(e['note'])} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    text = render()
    if "--write" in sys.argv:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {OUTPUT_FILE}")
    else:
        print(text, end="")

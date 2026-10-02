"""The tool layer: how the agent is allowed to act.

A Tool is a Python function plus a description the model reads. The
ToolRegistry is the single doorway every tool call passes through, and it
enforces the rules that must hold no matter what the rulebook or the
customer says:

  - nothing happens after the conversation is handed to a person;
  - tools marked requires_verification refuse until identity is verified;
  - inputs must match the tool's declared fields.

A tool that cannot proceed raises ToolError with a plain-English reason. The
model receives that reason and can recover (ask again, explain, hand off).
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple


class ToolError(Exception):
    """A refusal the model should read and react to."""


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable                    # called as handler(session, **inputs)
    properties: Dict[str, dict] = field(default_factory=dict)  # input fields
    required: List[str] = field(default_factory=list)
    requires_verification: bool = True   # safe default: locked until verified

    def schema(self) -> dict:
        """The tool as described to the model."""
        return {
            "name": self.name,
            "description": self.description,
            "strict": True,  # the API guarantees inputs match the fields below
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": self.required,
                "additionalProperties": False,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Two tools are both named {tool.name!r}")
        self._tools[tool.name] = tool

    def schemas(self) -> List[dict]:
        return [t.schema() for t in self._tools.values()]

    def execute(self, session, name: str, tool_input: dict) -> Tuple[str, bool]:
        """Run one tool call. Returns (result_text, is_error)."""
        session.log.record("tool_call", tool=name, input=tool_input)
        try:
            result = self._run(session, name, tool_input)
            text, is_error = json.dumps(result, ensure_ascii=False), False
        except ToolError as e:
            text, is_error = str(e), True
        except Exception as e:  # a bug in a tool must not crash the chat
            session.log.record("tool_crash", tool=name, error=repr(e))
            text, is_error = "Internal error. Apologise and hand off to a human agent.", True
        session.log.record("tool_result", tool=name, is_error=is_error, result=text)
        return text, is_error

    def _run(self, session, name: str, tool_input: dict):
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"There is no tool named {name!r}.")
        if session.handed_off and name != "handoff_to_human":
            raise ToolError(
                "This conversation has been handed off to a human agent. "
                "No further actions are allowed."
            )
        if tool.requires_verification and not session.verified:
            raise ToolError(
                "Identity not verified. Verify the customer with verify_identity "
                "before using this tool."
            )
        missing = [f for f in tool.required if f not in tool_input]
        unknown = [f for f in tool_input if f not in tool.properties]
        if missing or unknown:
            raise ToolError(f"Invalid input. Missing: {missing}. Not accepted: {unknown}.")
        return tool.handler(session, **tool_input)

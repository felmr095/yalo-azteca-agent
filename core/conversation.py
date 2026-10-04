"""One conversation, fully wired: database, session, log, tools and model.

This is the single entry point. The chat screen, the terminal chat and the
tests all create a Conversation, so there is exactly one place where the
core and the use-case modules are assembled.
"""

from typing import Optional

import config
from core import agent, rulebook
from core.clock import within_contact_hours
from core.core_tools import CORE_TOOLS
from core.logger import ConversationLog
from core.modules import load_modules
from core.session import start_session
from core.tools import ToolRegistry
from data import seed


class OutboundNotAllowed(Exception):
    """The bank may not start this conversation now. The message says why,
    for the person running the demo; it is never shown to the customer."""


class Conversation:
    def __init__(self, phone: str, client=None, log_directory: Optional[str] = None):
        self.modules = load_modules()
        self.log = ConversationLog(log_directory) if log_directory else ConversationLog()

        # A private copy of the bank: core data, then each module's own.
        self.conn = seed.new_database()
        for module in self.modules:
            if module.setup_database:
                module.setup_database(self.conn)

        self.session = start_session(self.conn, self.log, phone)

        self.registry = ToolRegistry()
        for tool in CORE_TOOLS:
            self.registry.add(tool)
        for module in self.modules:
            for tool in module.tools:
                self.registry.add(tool)

        self._client = client
        self.messages = []  # the conversation in the API's format
        self.log.record("session_start", phone=phone, customer_id=self.session.customer_id,
                        modules=[m.name for m in self.modules])

    def call_tool(self, name: str, tool_input: dict):
        """Run a tool exactly as the agent would. Returns (text, is_error)."""
        return self.registry.execute(self.session, name, tool_input)

    def outcome_summary(self) -> dict:
        """What the conversation has achieved so far, as {label: text}.

        Identity comes from the session; everything else is read from the
        database, so it shows what was really recorded, not what was said.
        """
        summary = {"Identity": "verified" if self.session.verified else "not verified"}
        ticket = self.conn.execute(
            "SELECT id, reason FROM handoff_tickets ORDER BY id DESC LIMIT 1").fetchone()
        summary["Handoff"] = (
            f"ticket HT-{ticket['id']:04d}, reason {ticket['reason']}" if ticket else "none")
        if self.session.customer_id is not None:
            for module in self.modules:
                if module.outcome:
                    summary.update(module.outcome(self.conn, self.session.customer_id))
        return summary

    def send(self, user_text: str) -> str:
        """Pass one customer message to the agent and return its reply."""
        self.log.record("user_message", text=user_text)
        return self._agent_turn(user_text)

    def open(self, module_name: str) -> str:
        """Have the agent write first, as an outbound contact for a module.

        Raises OutboundNotAllowed if the bank may not contact this customer
        now.
        """
        try:
            note = self.opening_note(module_name)
        except OutboundNotAllowed as e:
            self.log.record("outbound_blocked", module=module_name, reason=str(e))
            raise
        self.log.record("outbound_start", module=module_name)
        return self._agent_turn(note)

    def opening_note(self, module_name: str) -> str:
        """The internal note that starts an outbound conversation.

        The model is told why the bank is reaching out and the account
        holder's first name, so it can ask for the right person. It is told
        nothing else about the customer.
        """
        module = next(m for m in self.modules if m.name == module_name)
        if self.session.customer_id is None:
            raise OutboundNotAllowed("This phone number does not belong to a customer.")
        if config.ENFORCE_CONTACT_HOURS and not within_contact_hours():
            raise OutboundNotAllowed(
                f"Outside contact hours ({config.CONTACT_HOUR_START}:00 to "
                f"{config.CONTACT_HOUR_END}:00, {config.TIME_ZONE})."
            )
        if module.outbound_check:
            reason = module.outbound_check(self.conn, self.session.customer_id)
            if reason:
                raise OutboundNotAllowed(reason)
        owner = self.conn.execute(
            "SELECT first_name FROM customers WHERE id = ?", (self.session.customer_id,)
        ).fetchone()
        return (
            "[Internal note, not written by the customer] The bank is starting this "
            f"conversation. Reason: {module.outbound_reason}. Account holder's first "
            f"name: {owner['first_name']}. The customer has not written anything yet. "
            "Write your opening message."
        )

    def _agent_turn(self, text: str) -> str:
        if self._client is None:
            self._client = agent.make_client()
        reply = agent.run_turn(
            client=self._client,
            system=rulebook.build_system_prompt(self.modules),  # re-read so edits apply live
            messages=self.messages,
            user_text=text,
            tools=self.registry.schemas(),
            execute_tool=self.call_tool,
        )
        self.log.record("assistant_message", text=reply)
        return reply

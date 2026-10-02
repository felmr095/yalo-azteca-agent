"""One conversation, fully wired: database, session, log, tools and model.

This is the single entry point. The chat screen, the terminal chat and the
tests all create a Conversation, so there is exactly one place where the
core and the use-case modules are assembled.
"""

from typing import Optional

from core import agent, rulebook
from core.core_tools import CORE_TOOLS
from core.logger import ConversationLog
from core.modules import load_modules
from core.session import start_session
from core.tools import ToolRegistry
from data import seed


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

    def send(self, user_text: str) -> str:
        """Pass one customer message to the agent and return its reply."""
        self.log.record("user_message", text=user_text)
        return self._agent_turn(user_text)

    def open(self, module_name: str) -> str:
        """Have the agent write first, as an outbound contact for a module.

        The model is told why the bank is reaching out and the account
        holder's name, so it can ask for the right person. It is told
        nothing else about the customer.
        """
        module = next(m for m in self.modules if m.name == module_name)
        owner = self.conn.execute(
            "SELECT full_name FROM customers WHERE id = ?", (self.session.customer_id,)
        ).fetchone()
        trigger = (
            "[Internal note, not written by the customer] The bank is starting this "
            f"conversation. Reason: {module.outbound_reason}. Account holder's name: "
            f"{owner['full_name'] if owner else 'unknown'}. The customer has not "
            "written anything yet. Write your opening message."
        )
        self.log.record("outbound_start", module=module_name)
        return self._agent_turn(trigger)

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

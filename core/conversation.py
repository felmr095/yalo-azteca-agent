"""One conversation, fully wired: database, session, log, tools and model.

This is the single entry point. The chat screen, the terminal chat and the
tests all create a Conversation and call send(), so there is exactly one
place where the pieces are assembled.
"""

from core import agent, rulebook
from core.core_tools import CORE_TOOLS
from core.logger import ConversationLog
from core.session import start_session
from core.tools import ToolRegistry
from data import seed


class Conversation:
    def __init__(self, phone: str, client=None):
        self.log = ConversationLog()
        self.conn = seed.new_database()  # private copy of the bank
        self.session = start_session(self.conn, self.log, phone)
        self.registry = ToolRegistry()
        for tool in CORE_TOOLS:
            self.registry.add(tool)
        self.client = client or agent.make_client()
        self.messages = []  # the conversation in the API's format
        self.log.record("session_start", phone=phone, customer_id=self.session.customer_id)

    def send(self, user_text: str) -> str:
        """Pass one customer message to the agent and return its reply."""
        self.log.record("user_message", text=user_text)
        reply = agent.run_turn(
            client=self.client,
            system=rulebook.build_system_prompt(),  # re-read so edits apply live
            messages=self.messages,
            user_text=user_text,
            tools=self.registry.schemas(),
            execute_tool=lambda name, tool_input: self.registry.execute(
                self.session, name, tool_input
            ),
        )
        self.log.record("assistant_message", text=reply)
        return reply

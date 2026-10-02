"""Records everything that happens in a conversation.

Each event (customer message, agent reply, tool call, tool result, outcome)
is one line of JSON in logs/<session_id>.jsonl, with a timestamp. The same
events are kept in memory so the chat screen can show and download them,
because files do not survive restarts on Streamlit Community Cloud.
"""

import json
import os
import uuid
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


class ConversationLog:
    def __init__(self, directory: str = LOG_DIR):
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.events = []
        self.path = os.path.join(directory, f"{self.session_id}.jsonl")

    def record(self, event_type: str, **data) -> None:
        event = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "session_id": self.session_id,
            "type": event_type,
            **data,
        }
        self.events.append(event)
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass  # a read-only disk must not break the conversation

    def as_text(self) -> str:
        return "\n".join(json.dumps(e, ensure_ascii=False) for e in self.events)

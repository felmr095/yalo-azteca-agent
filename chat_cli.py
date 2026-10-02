"""Chat with the agent in the terminal. Run with: python chat_cli.py

Quicker than the web app for trying out a rulebook change. Tool calls are
printed as they happen. Type "salir" to quit.
"""

from core.conversation import Conversation
from data.seed import CUSTOMERS


def pick_phone() -> str:
    print("Which customer's phone is this chat coming from?\n")
    for i, c in enumerate(CUSTOMERS, start=1):
        print(f"  {i}. {c['full_name']}  ({c['phone']})")
    print("  0. An unknown number\n")
    choice = input("Number [1]: ").strip() or "1"
    if choice == "0":
        return "+52 00 0000 0000"
    return CUSTOMERS[int(choice) - 1]["phone"]


def main():
    conversation = Conversation(pick_phone())
    print('\nEscriba su mensaje ("salir" para terminar).\n')
    while True:
        user_text = input("Cliente: ").strip()
        if user_text.lower() in ("salir", "exit", "quit"):
            break
        if not user_text:
            continue
        shown = len(conversation.log.events)
        reply = conversation.send(user_text)
        for event in conversation.log.events[shown:]:
            if event["type"] == "tool_call":
                print(f"   [tool] {event['tool']} {event['input']}")
            elif event["type"] == "tool_result":
                status = "REFUSED" if event["is_error"] else "ok"
                print(f"   [{status}] {event['result']}")
        print(f"\nAgente: {reply}\n")
    print(f"Log saved to {conversation.log.path}")


if __name__ == "__main__":
    main()

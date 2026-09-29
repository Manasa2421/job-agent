"""Terminal version of the agent. For the app version, double-click Start-Job-Agent.command."""
import os
import select
import sys

import anthropic

import core
import storage
from tools.daily import daily_update

HELP = """Commands:
  /paste   paste long text (finish with a line: /end) - usually not needed, pasting works directly
  /daily   show today's update
  /web     turn web search on/off
  /clear   forget this conversation (long-term memories stay)
  /help    show this help
  /quit    exit"""


_buffer = b""


def _read_line(block: bool = True):
    """Reads one line straight from the keyboard input (no hidden buffering)."""
    global _buffer
    while b"\n" not in _buffer:
        if not block and not select.select([0], [], [], 0.15)[0]:
            return None
        chunk = os.read(0, 65536)
        if not chunk:
            if _buffer:
                line, _buffer = _buffer, b""
                return line.decode("utf-8", "ignore")
            raise EOFError
        _buffer += chunk
    line, _buffer = _buffer.split(b"\n", 1)
    return line.decode("utf-8", "ignore")


def read_input(prompt: str) -> str:
    """Reads one message. If several lines are pasted at once, they become ONE message."""
    print(prompt, end="", flush=True)
    lines = [_read_line()]
    while True:
        more = _read_line(block=False)
        if more is None:
            break
        lines.append(more)
    return "\n".join(lines).strip()


def read_paste() -> str:
    print("Paste your text. Type /end on a new line when finished.")
    lines = []
    while True:
        line = _read_line()
        if line.strip() == "/end":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    try:
        client = core.get_client()
    except core.MissingKeyError as e:
        sys.exit(str(e))
    history = storage.load_history()
    web = False
    print("\n" + daily_update() + "\n")
    print("Agent ready! Type /help for commands.\n")

    while True:
        try:
            text = read_input("You: ")
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        cmd = text.lower()
        if cmd == "/quit":
            break
        if cmd == "/help":
            print(HELP + "\n"); continue
        if cmd == "/daily":
            print("\n" + daily_update() + "\n"); continue
        if cmd == "/end":
            print("(/end is only used to finish a /paste. Nothing to finish.)\n"); continue
        if cmd == "/web":
            web = not web
            print(f"Web search is now {'ON' if web else 'OFF'}.\n"); continue
        if cmd == "/clear":
            history = []
            storage.clear_history()
            print("Conversation cleared.\n"); continue
        if cmd == "/paste":
            pasted = read_paste()
            note = read_input("What should I do with it? (Enter = ATS check against my resume): ")
            text = f"{note or 'Here is a job description. Run an ATS check against my resume.'}\n\n{pasted}"

        try:
            reply = core.run_turn(client, history, text, web=web, plain_text=True,
                                  on_tool=lambda name: print(f"  [working: {name}]"))
        except anthropic.APIError as e:
            print(f"\n[API error] {e}\n")
            continue
        print(f"\nAgent: {reply}\n")
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
        storage.save_history(history)


if __name__ == "__main__":
    main()

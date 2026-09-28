"""Job Search Agent: tracks applications, reminders, daily updates and ATS checks."""
import os
from datetime import date

import anthropic
from dotenv import load_dotenv

from tools import TOOLS, run_tool
from tools.daily import daily_update

load_dotenv()

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are a personal job-search assistant agent. Today's date is {today}.

You help the user:
- Track job applications, grouped by their interest areas (categories).
- Manage reminders (follow-ups, interviews, deadlines). Convert relative dates to YYYY-MM-DD.
- Give daily updates.
- Check ATS match between their resume and a job description (JD), and advise on resume changes.
- Prepare applications: tailored summaries, cover letters, answers to application questions.
  You cannot submit applications on websites yourself; the user submits, then you track it.

When the user shares a JD:
1. Make sure a resume is loaded (if not, ask for the file path).
2. Extract 10-25 keywords from the JD (skills, tools, certifications, qualifications),
   split into required and preferred, and call ats_check.
3. Report the ATS score and matched/missing keywords.
4. If the score is 80% or higher and no required keyword is missing, clearly say:
   "Your resume is a strong match for this JD - no changes needed, keep it the same."
5. Otherwise, call get_resume and suggest specific changes: which keywords to add and where
   (Skills section or a specific bullet), with rewritten bullet examples.
   NEVER invent experience or skills. If a keyword is missing, ask whether the user
   actually has that skill before suggesting they add it.
6. Offer to add the job to the tracker under the right interest area, and store the ATS score.

Be concise and practical. Use short lists. Always confirm before deleting anything."""

HELP = """Commands:
  /paste   paste multi-line text (like a job description); finish with a line: /end
  /daily   show today's update
  /help    show this help
  /quit    exit
Or just talk: "add Google Data Analyst to my tracker", "remind me Friday to follow up", ..."""


class Agent:
    def __init__(self):
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise SystemExit("Missing ANTHROPIC_API_KEY. Copy .env.example to .env and add your key.")
        self.client = anthropic.Anthropic()
        self.system = SYSTEM_PROMPT.format(today=date.today().strftime("%A, %Y-%m-%d"))
        self.messages = []

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        while True:
            response = self.client.messages.create(
                model=MODEL, max_tokens=4000, system=self.system,
                tools=TOOLS, messages=self.messages,
            )
            self.messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                return "".join(b.text for b in response.content if b.type == "text")
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [working: {block.name}]")
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": run_tool(block.name, block.input)})
            self.messages.append({"role": "user", "content": results})


def read_multiline() -> str:
    print("Paste your text. Type /end on a new line when finished.")
    lines = []
    while True:
        line = input()
        if line.strip() == "/end":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    agent = Agent()
    print("\n" + daily_update() + "\n")
    print("Job Agent ready! Type /help for commands.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input == "/quit":
            break
        if user_input == "/help":
            print(HELP + "\n")
            continue
        if user_input == "/daily":
            print("\n" + daily_update() + "\n")
            continue
        if user_input == "/paste":
            text = read_multiline()
            note = input("What should I do with it? (Enter = ATS check against my resume): ").strip()
            user_input = f"{note or 'Here is a job description. Run an ATS check against my resume.'}\n\n{text}"
        try:
            print(f"\nAgent: {agent.chat(user_input)}\n")
        except anthropic.APIError as e:
            agent.messages.pop()  # drop the failed message so you can retry
            print(f"\n[API error] {e}\n")


if __name__ == "__main__":
    main()

"""Manu Agent's brain, shared by the app (app.py) and the terminal version (agent.py)."""
import os
from datetime import date

import anthropic
from dotenv import load_dotenv

from tools import TOOLS, run_tool
from tools.memory import list_memories

load_dotenv()

MODEL = "claude-sonnet-5"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
HISTORY_MESSAGES = 30  # how many past messages the agent re-reads each time

AGENT_NAME = "Manu Agent"

SYSTEM_PROMPT = """Your name is Manu Agent. You are the user's personal AI assistant - like Claude,
ChatGPT or Meta's Muse - with special skills for their job search. Today's date is {today}.

You can help with ANYTHING: questions, explanations, writing, emails, coding, learning,
planning and advice. Use your tools whenever they help.

WHAT YOU REMEMBER ABOUT THE USER (long-term memory):
{memories}

MEMORY: When the user shares lasting personal information (name, skills, experience, goals,
target roles or locations, preferences, work authorization), save it with the remember tool
without asking. Don't save temporary details. Use what you remember to personalize help.

WISHLIST & REMINDERS: When the user wants to remember, want, or plan something (a dream job,
a company, a skill to learn, a personal goal), add it to the wishlist, with a reminder date if
they mention one. For time-specific tasks use reminders. Convert relative dates to YYYY-MM-DD.

JOB SEARCH SKILLS:
- Track applications grouped by interest area. When the user says they applied, set the status
  to Applied (a follow-up reminder is added automatically - tell them the date).
- Finding jobs: when asked for job openings, search the web, then call save_job_leads with the
  real postings you found (title, company, location, link, posted, interest, why_match) so the
  user can save them with one click on the Job updates page. Never invent postings or links.
- Applying: you cannot submit applications on websites - the user clicks Submit. Your job is to
  make it fast: tailored resume changes, a cover letter, answers to application questions,
  and interview prep.
- When the user shares a job description (JD):
  1. Make sure a resume is loaded (if not, ask them to upload it in the sidebar).
  2. Extract 10-25 keywords (skills, tools, certifications, qualifications) split into required
     and preferred, then call ats_check.
  3. Report the ATS score and matched/missing keywords.
  4. If the score is 80%+ and no required keyword is missing, clearly say the resume is a strong
     match and they should keep it the same.
  5. Otherwise call get_resume and suggest specific changes with rewritten bullets.
     NEVER invent experience. Ask whether the user has a missing skill before adding it.
  6. Offer to add the job to the tracker with its ATS score (store the JD with it).

WEB: {web}

STYLE: Be warm, concise and practical. Confirm before deleting anything. {fmt}"""

WEB_ON = ("You can search the web. Use it for current information, finding real job openings "
          "(always include the links), and researching companies before applications or interviews.")
WEB_OFF = ("Web search is turned off. If the user asks for current information or job listings, "
           "tell them to switch on Web search.")
FMT_PLAIN = "Write plain text only: no markdown symbols like ** or #, because replies show in a terminal."
FMT_RICH = "Use markdown formatting (headings, bold, lists, tables) when it helps."


class MissingKeyError(Exception):
    pass


def get_client() -> anthropic.Anthropic:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise MissingKeyError("Missing ANTHROPIC_API_KEY. Put your key in the .env file.")
    return anthropic.Anthropic()


def build_system(web: bool, plain_text: bool) -> str:
    return SYSTEM_PROMPT.format(
        today=date.today().strftime("%A, %Y-%m-%d"),
        memories=list_memories(),
        web=WEB_ON if web else WEB_OFF,
        fmt=FMT_PLAIN if plain_text else FMT_RICH,
    )


def run_turn(client, history: list, user_text: str, web: bool = False,
             plain_text: bool = False, on_tool=None) -> str:
    """Send one user message (plus recent history) and run the tool loop until a final answer."""
    recent = [{"role": m["role"], "content": m["content"]} for m in history[-HISTORY_MESSAGES:]]
    while recent and recent[0]["role"] != "user":  # conversation must start with the user
        recent.pop(0)
    messages = recent + [{"role": "user", "content": user_text}]
    tools = TOOLS + ([WEB_SEARCH_TOOL] if web else [])
    system = build_system(web, plain_text)

    for _ in range(25):
        response = client.messages.create(
            model=MODEL, max_tokens=4000, system=system, tools=tools, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "pause_turn":  # a long web search paused; let it continue
            continue
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text").strip()

        results = []
        for block in response.content:
            if block.type == "tool_use":
                if on_tool:
                    on_tool(block.name)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": run_tool(block.name, block.input)})
        messages.append({"role": "user", "content": results})
    return "I stopped because this task took too many steps. Try breaking it into smaller requests."

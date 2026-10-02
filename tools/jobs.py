"""Job leads: new job postings the agent finds on the web, ready to save to the tracker."""
from datetime import datetime
import storage


def save_job_leads(jobs: list) -> str:
    data = storage.load()
    leads = []
    for j in jobs:
        if not j.get("title") or not j.get("company"):
            continue
        leads.append({
            "title": j.get("title", ""), "company": j.get("company", ""),
            "location": j.get("location", ""), "link": j.get("link", ""),
            "posted": j.get("posted", ""), "interest": j.get("interest", ""),
            "why_match": j.get("why_match", ""),
        })
    data["job_leads"] = leads
    data["job_leads_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    storage.save(data)
    return f"Saved {len(leads)} job leads. The user can add them to the tracker from the Job updates page."


def list_job_leads() -> str:
    data = storage.load()
    if not data["job_leads"]:
        return "No job leads yet."
    return f"Found on {data['job_leads_updated']}:\n" + "\n".join(
        f"- {j['title']} @ {j['company']} ({j['location']}) {j['link']}" for j in data["job_leads"])


TOOLS = [
    {
        "name": "save_job_leads",
        "description": ("Save real job postings you found with web search so the user can add them to their "
                        "tracker with one click. Only include postings with a real link you actually found."),
        "input_schema": {
            "type": "object",
            "properties": {
                "jobs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "company": {"type": "string"},
                            "location": {"type": "string"},
                            "link": {"type": "string"},
                            "posted": {"type": "string", "description": "e.g. '2 days ago' or a date"},
                            "interest": {"type": "string", "description": "Which of the user's interest areas"},
                            "why_match": {"type": "string", "description": "One short line on why it fits"},
                        },
                        "required": ["title", "company", "link"],
                    },
                }
            },
            "required": ["jobs"],
        },
    },
    {
        "name": "list_job_leads",
        "description": "Show the most recent job leads found.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

FUNCTIONS = {"save_job_leads": save_job_leads, "list_job_leads": list_job_leads}

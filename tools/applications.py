"""Track job applications: add, update status, list, delete."""
from datetime import date, timedelta

import storage

FOLLOW_UP_DAYS = 7


def _add_follow_up(data, app) -> str:
    """When you apply, automatically add a follow-up reminder (once per application)."""
    if any(r.get("app_id") == app["id"] and r["text"].startswith("Follow up") for r in data["reminders"]):
        return ""
    due = (date.today() + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
    data["reminders"].append({"id": storage.new_id(data), "text": f"Follow up on {app['role']} @ {app['company']}",
                              "due_date": due, "due_time": "", "app_id": app["id"], "done": False})
    return f" Follow-up reminder set for {due}."

STATUSES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected", "Withdrawn", "No Response"]


def _find(data, app_id):
    return next((a for a in data["applications"] if a["id"] == app_id), None)


def _fmt(a) -> str:
    ats = f" | ATS {a['ats_score']}%" if a.get("ats_score") is not None else ""
    applied = f" | applied {a['date_applied']}" if a.get("date_applied") else ""
    return f"#{a['id']} {a['role']} @ {a['company']} [{a['interest']}] - {a['status']}{applied}{ats}"


def add_application(company: str, role: str, interest: str, status: str = "Applied",
                    job_link: str = "", location: str = "", notes: str = "", date_applied: str = "",
                    job_description: str = "") -> str:
    data = storage.load()
    if interest not in data["interests"]:
        data["interests"].append(interest)
    app = {
        "id": storage.new_id(data), "company": company, "role": role, "interest": interest,
        "status": status, "job_link": job_link, "location": location, "notes": notes,
        "date_applied": date_applied or (storage.today() if status == "Applied" else ""),
        "last_updated": storage.today(), "ats_score": None, "job_description": job_description,
        "history": [{"date": storage.today(), "status": status}],
    }
    data["applications"].append(app)
    extra = _add_follow_up(data, app) if status == "Applied" else ""
    storage.save(data)
    return "Added: " + _fmt(app) + extra


def update_application(app_id: int, status: str = "", notes: str = "", job_link: str = "",
                       job_description: str = "") -> str:
    data = storage.load()
    app = _find(data, app_id)
    if not app:
        return f"No application with id {app_id}."
    extra = ""
    if job_description:
        app["job_description"] = job_description
    if status == "Applied" and app["status"] != "Applied":
        extra = _add_follow_up(data, app)
    if status:
        app["status"] = status
        app["history"].append({"date": storage.today(), "status": status})
        if status == "Applied" and not app.get("date_applied"):
            app["date_applied"] = storage.today()
    if notes:
        app["notes"] = (app["notes"] + " | " if app["notes"] else "") + notes
    if job_link:
        app["job_link"] = job_link
    app["last_updated"] = storage.today()
    storage.save(data)
    return "Updated: " + _fmt(app) + extra


def list_applications(interest: str = "", status: str = "") -> str:
    apps = storage.load()["applications"]
    if interest:
        apps = [a for a in apps if a["interest"].lower() == interest.lower()]
    if status:
        apps = [a for a in apps if a["status"].lower() == status.lower()]
    if not apps:
        return "No applications found."
    groups = {}
    for a in apps:
        groups.setdefault(a["interest"], []).append(a)
    lines = []
    for name, items in groups.items():
        lines.append(f"== {name} ({len(items)}) ==")
        lines += [_fmt(a) + (f"\n    notes: {a['notes']}" if a["notes"] else "") for a in items]
    return "\n".join(lines)


def delete_application(app_id: int) -> str:
    data = storage.load()
    before = len(data["applications"])
    data["applications"] = [a for a in data["applications"] if a["id"] != app_id]
    storage.save(data)
    return "Deleted." if len(data["applications"]) < before else f"No application with id {app_id}."


TOOLS = [
    {
        "name": "add_application",
        "description": "Add a job application to the tracker. 'interest' is the category it belongs to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "role": {"type": "string"},
                "interest": {"type": "string", "description": "Interest category, e.g. 'Data Analyst'"},
                "status": {"type": "string", "enum": STATUSES},
                "job_link": {"type": "string"},
                "location": {"type": "string"},
                "notes": {"type": "string"},
                "date_applied": {"type": "string", "description": "YYYY-MM-DD; defaults to today if status is Applied"},
                "job_description": {"type": "string", "description": "Full JD text if the user shared it"},
            },
            "required": ["company", "role", "interest"],
        },
    },
    {
        "name": "update_application",
        "description": ("Update an application's status, add notes (appended), set the job link or store the JD. "
                        "Setting status to Applied automatically adds a follow-up reminder in 7 days."),
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {"type": "integer"},
                "status": {"type": "string", "enum": STATUSES},
                "notes": {"type": "string"},
                "job_link": {"type": "string"},
                "job_description": {"type": "string"},
            },
            "required": ["app_id"],
        },
    },
    {
        "name": "list_applications",
        "description": "List applications grouped by interest. Optionally filter by interest or status.",
        "input_schema": {
            "type": "object",
            "properties": {"interest": {"type": "string"}, "status": {"type": "string"}},
        },
    },
    {
        "name": "delete_application",
        "description": "Delete an application by id. Confirm with the user first.",
        "input_schema": {"type": "object", "properties": {"app_id": {"type": "integer"}}, "required": ["app_id"]},
    },
]

FUNCTIONS = {
    "add_application": add_application,
    "update_application": update_application,
    "list_applications": list_applications,
    "delete_application": delete_application,
}

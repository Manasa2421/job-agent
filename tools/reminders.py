"""Reminders with due dates (follow-ups, interviews, deadlines...)."""
import storage


def add_reminder(text: str, due_date: str, due_time: str = "", app_id: int = 0) -> str:
    data = storage.load()
    r = {"id": storage.new_id(data), "text": text, "due_date": due_date,
         "due_time": due_time, "app_id": app_id or None, "done": False}
    data["reminders"].append(r)
    storage.save(data)
    when = f"{due_date} {due_time}".strip()
    return f"Reminder #{r['id']} set: '{text}' on {when}"


def list_reminders(include_done: bool = False) -> str:
    items = [r for r in storage.load()["reminders"] if include_done or not r["done"]]
    if not items:
        return "No reminders."
    items.sort(key=lambda r: (r["due_date"], r["due_time"]))
    return "\n".join(
        f"#{r['id']} {'[done] ' if r['done'] else ''}{r['due_date']} {r['due_time']} - {r['text']}".replace("  ", " ")
        for r in items
    )


def complete_reminder(reminder_id: int) -> str:
    data = storage.load()
    for r in data["reminders"]:
        if r["id"] == reminder_id:
            r["done"] = True
            storage.save(data)
            return f"Marked reminder #{reminder_id} as done."
    return f"No reminder with id {reminder_id}."


def delete_reminder(reminder_id: int) -> str:
    data = storage.load()
    before = len(data["reminders"])
    data["reminders"] = [r for r in data["reminders"] if r["id"] != reminder_id]
    storage.save(data)
    return "Deleted." if len(data["reminders"]) < before else f"No reminder with id {reminder_id}."


TOOLS = [
    {
        "name": "add_reminder",
        "description": "Add a reminder. Convert relative dates like 'tomorrow' to YYYY-MM-DD using today's date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                "due_time": {"type": "string", "description": "Optional, e.g. 14:30"},
                "app_id": {"type": "integer", "description": "Optional related application id"},
            },
            "required": ["text", "due_date"],
        },
    },
    {
        "name": "list_reminders",
        "description": "List reminders sorted by date.",
        "input_schema": {"type": "object", "properties": {"include_done": {"type": "boolean"}}},
    },
    {
        "name": "complete_reminder",
        "description": "Mark a reminder as done.",
        "input_schema": {"type": "object", "properties": {"reminder_id": {"type": "integer"}}, "required": ["reminder_id"]},
    },
    {
        "name": "delete_reminder",
        "description": "Delete a reminder.",
        "input_schema": {"type": "object", "properties": {"reminder_id": {"type": "integer"}}, "required": ["reminder_id"]},
    },
]

FUNCTIONS = {
    "add_reminder": add_reminder,
    "list_reminders": list_reminders,
    "complete_reminder": complete_reminder,
    "delete_reminder": delete_reminder,
}

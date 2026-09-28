"""Your interest areas (e.g. 'Data Analyst', 'Software Engineer'). Applications are grouped by these."""
import storage


def add_interest(name: str) -> str:
    data = storage.load()
    if any(i.lower() == name.lower() for i in data["interests"]):
        return f"'{name}' is already in your interests."
    data["interests"].append(name)
    storage.save(data)
    return f"Added interest '{name}'. Interests now: {', '.join(data['interests'])}"


def remove_interest(name: str) -> str:
    data = storage.load()
    before = len(data["interests"])
    data["interests"] = [i for i in data["interests"] if i.lower() != name.lower()]
    storage.save(data)
    return "Removed." if len(data["interests"]) < before else f"'{name}' not found."


def list_interests() -> str:
    interests = storage.load()["interests"]
    return ", ".join(interests) if interests else "No interests set yet."


TOOLS = [
    {
        "name": "add_interest",
        "description": "Add a job interest area/category, e.g. 'Data Analyst' or 'Frontend Developer'.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
    {
        "name": "remove_interest",
        "description": "Remove a job interest area.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
    {
        "name": "list_interests",
        "description": "List the user's job interest areas.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

FUNCTIONS = {"add_interest": add_interest, "remove_interest": remove_interest, "list_interests": list_interests}

"""Long-term memory: facts the agent learns about you (like Claude/ChatGPT/Muse memory)."""
import storage


def remember(fact: str) -> str:
    data = storage.load()
    if any(m["fact"].lower() == fact.lower() for m in data["memories"]):
        return "Already remembered."
    m = {"id": storage.new_id(data), "fact": fact, "date": storage.today()}
    data["memories"].append(m)
    storage.save(data)
    return f"Remembered (#{m['id']}): {fact}"


def forget(memory_id: int) -> str:
    data = storage.load()
    before = len(data["memories"])
    data["memories"] = [m for m in data["memories"] if m["id"] != memory_id]
    storage.save(data)
    return "Forgotten." if len(data["memories"]) < before else f"No memory with id {memory_id}."


def list_memories() -> str:
    mems = storage.load()["memories"]
    return "\n".join(f"#{m['id']} {m['fact']}" for m in mems) if mems else "Nothing remembered yet."


TOOLS = [
    {
        "name": "remember",
        "description": ("Save a lasting fact about the user to long-term memory (name, skills, experience, goals, "
                        "target roles/locations, preferences, work authorization). Not for temporary details."),
        "input_schema": {"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]},
    },
    {
        "name": "forget",
        "description": "Delete a memory by id when the user asks or it's no longer true.",
        "input_schema": {"type": "object", "properties": {"memory_id": {"type": "integer"}}, "required": ["memory_id"]},
    },
    {
        "name": "list_memories",
        "description": "List everything remembered about the user.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

FUNCTIONS = {"remember": remember, "forget": forget, "list_memories": list_memories}

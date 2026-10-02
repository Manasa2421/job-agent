"""Wishlist: jobs, companies, skills or anything you want - with optional reminder dates."""
import storage

CATEGORIES = ["Job", "Company", "Skill to learn", "Personal", "Other"]


def add_wishlist_item(item: str, category: str = "Other", remind_date: str = "", notes: str = "") -> str:
    data = storage.load()
    w = {"id": storage.new_id(data), "item": item, "category": category,
         "remind_date": remind_date, "notes": notes, "done": False, "added": storage.today()}
    data["wishlist"].append(w)
    storage.save(data)
    when = f" (reminder on {remind_date})" if remind_date else ""
    return f"Added to wishlist #{w['id']} [{category}]: {item}{when}"


def list_wishlist(category: str = "", include_done: bool = False) -> str:
    items = [w for w in storage.load()["wishlist"] if include_done or not w["done"]]
    if category:
        items = [w for w in items if w["category"].lower() == category.lower()]
    if not items:
        return "Wishlist is empty."
    lines = []
    for w in sorted(items, key=lambda w: (w["category"], w["remind_date"] or "9999")):
        date = f" - remind {w['remind_date']}" if w["remind_date"] else ""
        done = "[done] " if w["done"] else ""
        lines.append(f"#{w['id']} {done}[{w['category']}] {w['item']}{date}")
    return "\n".join(lines)


def complete_wishlist_item(item_id: int) -> str:
    data = storage.load()
    for w in data["wishlist"]:
        if w["id"] == item_id:
            w["done"] = True
            storage.save(data)
            return f"Marked wishlist item #{item_id} as done."
    return f"No wishlist item with id {item_id}."


def delete_wishlist_item(item_id: int) -> str:
    data = storage.load()
    before = len(data["wishlist"])
    data["wishlist"] = [w for w in data["wishlist"] if w["id"] != item_id]
    storage.save(data)
    return "Deleted." if len(data["wishlist"]) < before else f"No wishlist item with id {item_id}."


TOOLS = [
    {
        "name": "add_wishlist_item",
        "description": ("Add something to the user's wishlist: a dream job or company, a skill to learn, a personal "
                        "goal, anything. Optional reminder date (YYYY-MM-DD; convert 'next week' etc. from today)."),
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "category": {"type": "string", "enum": CATEGORIES},
                "remind_date": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["item"],
        },
    },
    {
        "name": "list_wishlist",
        "description": "List wishlist items, optionally filtered by category.",
        "input_schema": {"type": "object", "properties": {
            "category": {"type": "string"}, "include_done": {"type": "boolean"}}},
    },
    {
        "name": "complete_wishlist_item",
        "description": "Mark a wishlist item as done/achieved.",
        "input_schema": {"type": "object", "properties": {"item_id": {"type": "integer"}}, "required": ["item_id"]},
    },
    {
        "name": "delete_wishlist_item",
        "description": "Delete a wishlist item. Confirm with the user first.",
        "input_schema": {"type": "object", "properties": {"item_id": {"type": "integer"}}, "required": ["item_id"]},
    },
]

FUNCTIONS = {
    "add_wishlist_item": add_wishlist_item,
    "list_wishlist": list_wishlist,
    "complete_wishlist_item": complete_wishlist_item,
    "delete_wishlist_item": delete_wishlist_item,
}

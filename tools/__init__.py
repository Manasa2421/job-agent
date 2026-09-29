"""Collects every tool module. To add a new feature: create tools/your_feature.py
with TOOLS and FUNCTIONS, then add it to MODULES below."""
from . import interests, applications, reminders, resume_ats, daily, memory

MODULES = [interests, applications, reminders, resume_ats, daily, memory]

TOOLS = []
FUNCTIONS = {}
for module in MODULES:
    TOOLS.extend(module.TOOLS)
    FUNCTIONS.update(module.FUNCTIONS)


def run_tool(name: str, tool_input: dict) -> str:
    func = FUNCTIONS.get(name)
    if func is None:
        return f"Error: unknown tool '{name}'"
    try:
        return str(func(**tool_input))
    except Exception as e:
        return f"Error running {name}: {e}"

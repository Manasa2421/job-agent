"""Your daily update: reminders, follow-ups and a summary of your job search."""
from collections import Counter
from datetime import date, timedelta
import storage

FOLLOW_UP_AFTER_DAYS = 7


def daily_update() -> str:
    data = storage.load()
    today = date.today()
    t = today.isoformat()
    week = (today + timedelta(days=7)).isoformat()
    lines = [f"📅 DAILY UPDATE - {today.strftime('%A, %b %d, %Y')}", ""]

    open_r = sorted([r for r in data["reminders"] if not r["done"]], key=lambda r: (r["due_date"], r["due_time"]))
    overdue = [r for r in open_r if r["due_date"] < t]
    due_today = [r for r in open_r if r["due_date"] == t]
    upcoming = [r for r in open_r if t < r["due_date"] <= week]

    lines.append("🔔 REMINDERS")
    if not open_r:
        lines.append("  Nothing pending.")
    for r in overdue:
        lines.append(f"  ⚠️  OVERDUE #{r['id']}: {r['text']} (was due {r['due_date']})")
    for r in due_today:
        lines.append(f"  👉 TODAY #{r['id']}: {r['text']} {r['due_time']}".rstrip())
    for r in upcoming:
        lines.append(f"  • {r['due_date']} #{r['id']}: {r['text']}")

    wish = [w for w in data["wishlist"] if not w["done"]]
    wish_due = sorted([w for w in wish if w["remind_date"] and w["remind_date"] <= week], key=lambda w: w["remind_date"])
    lines += ["", "⭐ WISHLIST"]
    for w in wish_due:
        tag = "⚠️  OVERDUE" if w["remind_date"] < t else ("👉 TODAY" if w["remind_date"] == t else f"• {w['remind_date']}")
        lines.append(f"  {tag} #{w['id']} [{w['category']}] {w['item']}")
    if not wish_due:
        lines.append(f"  No wishlist reminders this week ({len(wish)} item(s) on your wishlist).")

    apps = data["applications"]
    cutoff = (today - timedelta(days=FOLLOW_UP_AFTER_DAYS)).isoformat()
    follow = [a for a in apps if a["status"] == "Applied" and a["last_updated"] <= cutoff]
    interviewing = [a for a in apps if a["status"] == "Interviewing"]

    lines += ["", "📨 SUGGESTED FOLLOW-UPS (applied 7+ days ago, no update)"]
    lines += [f"  • #{a['id']} {a['role']} @ {a['company']} (applied {a['date_applied']})" for a in follow] or ["  None."]

    lines += ["", "🎯 INTERVIEWING"]
    lines += [f"  • #{a['id']} {a['role']} @ {a['company']}" for a in interviewing] or ["  None yet."]

    lines += ["", "📊 SUMMARY"]
    if apps:
        by_status = Counter(a["status"] for a in apps)
        by_interest = Counter(a["interest"] for a in apps)
        week_ago = (today - timedelta(days=7)).isoformat()
        this_week = sum(1 for a in apps if a.get("date_applied") and a["date_applied"] >= week_ago)
        lines.append("  Total: " + str(len(apps)) + " | " + " | ".join(f"{k}: {v}" for k, v in by_status.items()))
        lines.append("  By interest: " + " | ".join(f"{k}: {v}" for k, v in by_interest.items()))
        lines.append(f"  Applied in the last 7 days: {this_week}")
    else:
        lines.append("  No applications tracked yet.")
    return "\n".join(lines)


def due_now() -> list:
    """Short list of things needing attention today (used for the app's banner)."""
    data = storage.load()
    t = date.today().isoformat()
    items = [f"Reminder: {r['text']}" for r in data["reminders"] if not r["done"] and r["due_date"] <= t]
    items += [f"Wishlist: {w['item']}" for w in data["wishlist"]
              if not w["done"] and w["remind_date"] and w["remind_date"] <= t]
    return items


TOOLS = [
    {
        "name": "daily_update",
        "description": "Get today's update: reminders, wishlist reminders, follow-ups needed, interviews, summary.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

FUNCTIONS = {"daily_update": daily_update}

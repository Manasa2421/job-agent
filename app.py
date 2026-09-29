"""App version of your agent: a chat window in your browser.
Start it by double-clicking Start-Job-Agent.command (or: streamlit run app.py)."""
from datetime import time

import anthropic
import pandas as pd
import streamlit as st

import core
import storage
from tools.applications import STATUSES, update_application
from tools.daily import daily_update
from tools.memory import forget
from tools.reminders import add_reminder, complete_reminder
from tools.resume_ats import load_resume

st.set_page_config(page_title="My AI Agent", page_icon="💼", layout="wide")

STARTERS = [
    "Help me check a job description against my resume",
    "Find Data Engineer jobs posted this week in Dallas",
    "Write a cover letter for my latest saved job",
    "Give me 5 interview questions for a Data Engineer role",
]

# ---------- Setup ----------
if "client" not in st.session_state:
    try:
        st.session_state.client = core.get_client()
    except core.MissingKeyError as e:
        st.error(f"{e} Then restart the app.")
        st.stop()
if "history" not in st.session_state:
    st.session_state.history = storage.load_history()

history = st.session_state.history

# ---------- Sidebar ----------
with st.sidebar:
    st.title("💼 My AI Agent")
    page = st.radio("Go to", ["💬 Chat", "📋 Applications", "🔔 Reminders", "📅 Daily update", "🧠 Memory"],
                    label_visibility="collapsed")
    st.divider()
    web = st.toggle("🌐 Web search", value=False,
                    help="Lets the agent search the internet for jobs, companies and current info.")

    st.subheader("📄 Resume")
    if storage.RESUME_FILE.exists():
        words = len(storage.RESUME_FILE.read_text(encoding="utf-8").split())
        st.caption(f"Resume loaded ({words} words). Upload a new one to replace it.")
    else:
        st.caption("No resume yet. Upload one to run ATS checks.")
    uploaded = st.file_uploader("Upload resume", type=["pdf", "docx", "txt"], label_visibility="collapsed")
    if uploaded and st.button("Use this resume", use_container_width=True):
        storage.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        path = storage.UPLOADS_DIR / uploaded.name
        path.write_bytes(uploaded.getvalue())
        st.success(load_resume(str(path)))

    st.divider()
    if st.button("Start a new chat", use_container_width=True):
        st.session_state.history = []
        storage.clear_history()
        st.rerun()


# ---------- Chat ----------
def chat_page():
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not history:
        st.markdown("### How can I help today?")
        st.caption("Ask anything, or paste a job description. Long text pastes work here.")
        cols = st.columns(2)
        for i, text in enumerate(STARTERS):
            if cols[i % 2].button(text, use_container_width=True, key=f"starter{i}"):
                st.session_state.pending = text
                st.rerun()

    prompt = st.chat_input("Message your agent...") or st.session_state.pop("pending", None)
    if not prompt:
        return

    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        activity = st.empty()
        try:
            with st.spinner("Thinking..."):
                reply = core.run_turn(
                    st.session_state.client, history, prompt, web=web,
                    on_tool=lambda name: activity.caption(f"🔧 Using {name.replace('_', ' ')}..."),
                )
        except anthropic.APIError as e:
            activity.empty()
            st.error(f"The AI service returned an error: {e}")
            return
        activity.empty()
        st.markdown(reply)
    history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": reply}])
    storage.save_history(history)


# ---------- Applications ----------
def applications_page():
    st.header("📋 Applications")
    apps = storage.load()["applications"]
    if not apps:
        st.info("No applications yet. In Chat, say: \"I applied to [role] at [company], add it to my tracker\".")
        return

    df = pd.DataFrame(apps)
    counts = df["status"].value_counts()
    cols = st.columns(len(counts))
    for col, (status, n) in zip(cols, counts.items()):
        col.metric(status, n)

    interests = ["All"] + sorted(df["interest"].unique().tolist())
    choice = st.selectbox("Interest area", interests)
    view = df if choice == "All" else df[df["interest"] == choice]
    show = ["id", "company", "role", "interest", "status", "ats_score", "date_applied", "last_updated", "job_link", "notes"]
    st.dataframe(view[[c for c in show if c in view.columns]], use_container_width=True, hide_index=True,
                 column_config={"job_link": st.column_config.LinkColumn("job_link"),
                                "ats_score": st.column_config.NumberColumn("ATS %")})

    st.subheader("Update a status")
    labels = {f"#{a['id']} {a['role']} @ {a['company']}": a["id"] for a in apps}
    c1, c2, c3 = st.columns([3, 2, 1])
    picked = c1.selectbox("Application", list(labels))
    new_status = c2.selectbox("New status", STATUSES)
    if c3.button("Update", use_container_width=True):
        st.success(update_application(labels[picked], status=new_status))
        st.rerun()


# ---------- Reminders ----------
def reminders_page():
    st.header("🔔 Reminders")
    with st.form("new_reminder", clear_on_submit=True):
        text = st.text_input("Reminder", placeholder="Follow up with the recruiter")
        c1, c2 = st.columns(2)
        due = c1.date_input("Date")
        at = c2.time_input("Time (optional)", value=time(9, 0))
        if st.form_submit_button("Add reminder") and text:
            add_reminder(text, due.isoformat(), at.strftime("%H:%M"))
            st.rerun()

    reminders = sorted([r for r in storage.load()["reminders"] if not r["done"]],
                       key=lambda r: (r["due_date"], r["due_time"]))
    if not reminders:
        st.info("Nothing pending.")
    today = storage.today()
    for r in reminders:
        c1, c2 = st.columns([6, 1])
        flag = "⚠️ " if r["due_date"] < today else ("👉 " if r["due_date"] == today else "")
        c1.write(f"{flag}**{r['due_date']} {r['due_time']}** {r['text']}")
        if c2.button("Done", key=f"done{r['id']}"):
            complete_reminder(r["id"])
            st.rerun()


# ---------- Daily update ----------
def daily_page():
    st.header("📅 Daily update")
    st.text(daily_update())


# ---------- Memory ----------
def memory_page():
    st.header("🧠 What your agent remembers")
    st.caption("Your agent saves lasting facts you share (skills, goals, preferences) and uses them in every chat.")
    mems = storage.load()["memories"]
    if not mems:
        st.info("Nothing yet. Try telling it in Chat: \"I'm a Data Engineer with 3 years of experience in Python and Spark.\"")
    for m in mems:
        c1, c2 = st.columns([6, 1])
        c1.write(m["fact"])
        if c2.button("Forget", key=f"forget{m['id']}"):
            forget(m["id"])
            st.rerun()


{"💬 Chat": chat_page, "📋 Applications": applications_page, "🔔 Reminders": reminders_page,
 "📅 Daily update": daily_page, "🧠 Memory": memory_page}[page]()

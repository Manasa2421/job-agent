"""Manu Agent - your personal AI assistant app, in your browser.
Start it by double-clicking Start-Job-Agent.command (or: streamlit run app.py)."""
from datetime import date, datetime, time, timedelta

import anthropic
import pandas as pd
import streamlit as st

import core
import storage
from tools.applications import STATUSES, add_application, update_application
from tools.daily import daily_update, due_now
from tools.email_sync import connect_email, disconnect_email, email_configured
from tools.memory import forget
from tools.reminders import add_reminder, complete_reminder
from tools.resume_ats import load_resume
from tools.wishlist import CATEGORIES, add_wishlist_item, complete_wishlist_item, delete_wishlist_item

st.set_page_config(page_title="Manu Agent", page_icon="🤖", layout="wide")

STARTERS = [
    "Help me check a job description against my resume",
    "Find Data Engineer jobs posted this week in Dallas",
    "Add 'learn Apache Airflow' to my wishlist and remind me next Friday",
    "Give me 5 interview questions for a Data Engineer role",
]
PAGES = ["💬 Chat", "📰 Job updates", "📋 Applications", "⭐ Wishlist", "🔔 Reminders", "📅 Daily update", "🧠 Memory"]
WEB_ERROR = ("Web search failed. It may need to be turned on for your account: in Claude Console, "
             "check your organization's privacy or tool settings for web search. Details: ")

# ---------- Setup ----------
if "client" not in st.session_state:
    try:
        st.session_state.client = core.get_client()
    except core.MissingKeyError as e:
        st.error(f"{e} Then restart the app.")
        st.stop()
if "history" not in st.session_state:
    st.session_state.history = storage.load_history()

client = st.session_state.client
history = st.session_state.history
AUTO_SYNC_HOURS = 6


def run_email_sync(days: int = 7) -> str:
    prompt = f"Sync my job applications from my email for the last {days} days (call sync_job_emails with days={days})."
    return core.run_turn(client, [], prompt)


def auto_sync_due() -> bool:
    data = storage.load()
    if not email_configured() or not data["settings"].get("auto_email_sync", True):
        return False
    last = data.get("last_email_sync")
    if not last:
        return True
    return datetime.now() - datetime.strptime(last, "%Y-%m-%d %H:%M") > timedelta(hours=AUTO_SYNC_HOURS)


if not st.session_state.get("auto_sync_checked"):
    st.session_state.auto_sync_checked = True
    if auto_sync_due():
        try:
            with st.spinner("📥 Checking your email for new job applications..."):
                st.session_state.sync_summary = run_email_sync(7)
        except anthropic.APIError as e:
            st.session_state.sync_summary = f"Email check failed: {e}"


def flash(msg: str):
    """Show a message after the page reloads."""
    st.session_state.flash = msg


def show_flash():
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))


# ---------- Sidebar ----------
with st.sidebar:
    st.title("🤖 Manu Agent")
    page = st.radio("Go to", PAGES, label_visibility="collapsed")
    st.divider()
    web = st.toggle("🌐 Web search in chat", value=False,
                    help="Lets Manu Agent search the internet for jobs, companies and current info.")

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
def show_sync_summary():
    if st.session_state.get("sync_summary"):
        with st.expander("📥 Latest email check", expanded=True):
            st.markdown(st.session_state.sync_summary)
            if st.button("Hide", key="hide_sync"):
                st.session_state.sync_summary = ""
                st.rerun()


def chat_page():
    show_sync_summary()
    due = due_now()
    if due:
        st.warning("**Due today:** " + " | ".join(due))

    for msg in history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else None):
            st.markdown(msg["content"])

    if not history:
        st.markdown("### Hi, I'm Manu Agent. How can I help today?")
        st.caption("Ask anything, or paste a job description. Long text pastes work here.")
        cols = st.columns(2)
        for i, text in enumerate(STARTERS):
            if cols[i % 2].button(text, use_container_width=True, key=f"starter{i}"):
                st.session_state.pending = text
                st.rerun()

    prompt = st.chat_input("Message Manu Agent...") or st.session_state.pop("pending", None)
    if not prompt:
        return

    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🤖"):
        activity = st.empty()
        try:
            with st.spinner("Thinking..."):
                reply = core.run_turn(client, history, prompt, web=web,
                                      on_tool=lambda n: activity.caption(f"🔧 {n.replace('_', ' ')}..."))
        except anthropic.APIError as e:
            activity.empty()
            st.error((WEB_ERROR if web else "The AI service returned an error: ") + str(e))
            return
        activity.empty()
        st.markdown(reply)
    history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": reply}])
    storage.save_history(history)


# ---------- Job updates ----------
def jobs_page():
    st.header("📰 Job updates")
    show_flash()
    data = storage.load()
    interests = data["interests"]
    st.caption("Looking for: " + (", ".join(interests) if interests
                                  else "no interests yet. Tell Manu Agent your target roles in Chat."))
    where = st.text_input("Location or preferences (optional)", placeholder="Dallas, TX or remote, entry level")

    if st.button("🔎 Find new jobs for me", type="primary"):
        roles = ", ".join(interests) or "the roles I'm targeting (use what you remember about me)"
        prompt = (f"Search the web for job postings from the last 7 days for: {roles}."
                  + (f" Location and preferences: {where}." if where else "")
                  + " Use what you remember about me. Find up to 10 real, currently open postings with direct "
                    "links. Then call save_job_leads with them. Finish with a 2-3 sentence summary.")
        try:
            with st.spinner("Searching the web for new jobs. This can take a minute..."):
                st.session_state.jobs_summary = core.run_turn(client, [], prompt, web=True)
        except anthropic.APIError as e:
            st.error(WEB_ERROR + str(e))
        data = storage.load()

    if st.session_state.get("jobs_summary"):
        st.info(st.session_state.jobs_summary)

    leads = data["job_leads"]
    if not leads:
        st.write("No job leads yet. Click **Find new jobs for me** to search.")
        return
    st.caption(f"Last searched: {data['job_leads_updated']}")
    tracked = {a.get("job_link") for a in data["applications"] if a.get("job_link")}
    for i, j in enumerate(leads):
        with st.container(border=True):
            st.markdown(f"**{j['title']}** at {j['company']}")
            meta = [x for x in [j.get("location"), j.get("posted") and f"posted {j['posted']}", j.get("interest")] if x]
            if meta:
                st.caption(" | ".join(meta))
            if j.get("why_match"):
                st.write(j["why_match"])
            c1, c2 = st.columns(2)
            if j.get("link"):
                c1.link_button("Open job posting", j["link"])
            if j.get("link") in tracked:
                c2.caption("✅ In your tracker")
            elif c2.button("Save to tracker", key=f"lead{i}"):
                add_application(j["company"], j["title"], j.get("interest") or (interests[0] if interests else "Other"),
                                status="Saved", job_link=j.get("link", ""), location=j.get("location", ""),
                                notes=j.get("why_match", ""))
                flash(f"Saved {j['title']} at {j['company']}. Open Applications to prepare it.")
                st.rerun()


# ---------- Applications ----------
def applications_page():
    st.header("📋 Applications")
    show_flash()
    show_sync_summary()
    tab_week, tab_all, tab_apply, tab_email = st.tabs(
        ["📆 This week", "📋 All applications", "✍️ Apply helper", "📧 Email sync"])
    apps = storage.load()["applications"]
    with tab_week:
        week_view(apps)
    with tab_all:
        all_view(apps)
    with tab_apply:
        apply_helper(apps)
    with tab_email:
        email_view()


def week_view(apps):
    today = date.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    cutoff = days[0].isoformat()
    week = sorted([a for a in apps if (a.get("date_applied") or "") >= cutoff],
                  key=lambda a: a["date_applied"], reverse=True)
    updated = [a for a in apps if a.get("last_updated", "") >= cutoff and a not in week]

    c1, c2, c3 = st.columns(3)
    c1.metric("Applied in the last 7 days", len(week))
    c2.metric("Interviews", sum(1 for a in apps if a["status"] == "Interviewing"))
    c3.metric("Other updates this week", len(updated))

    chart = pd.DataFrame({"Applications": [sum(1 for a in week if a["date_applied"] == d.isoformat()) for d in days]},
                         index=[d.strftime("%m/%d %a") for d in days])
    st.bar_chart(chart)

    if not week:
        st.info("No applications in the last 7 days yet. Connect your email in the Email sync tab and "
                "Manu Agent will find them for you.")
        return
    rows = [{"Date": a["date_applied"], "Company": a["company"], "Role": a["role"], "Interest": a["interest"],
             "Status": a["status"], "Source": "📧 Email" if "Auto-added from email" in (a.get("notes") or "") else "Manual",
             "Job link": a.get("job_link", "")} for a in week]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                 column_config={"Job link": st.column_config.LinkColumn("Job link")})


def all_view(apps):
    if not apps:
        st.info("No applications yet. Connect email (Email sync tab), save one from Job updates, or tell "
                "Manu Agent in Chat: \"I applied to [role] at [company]\".")
        return
    df = pd.DataFrame(apps)
    counts = df["status"].value_counts()
    for col, (status, n) in zip(st.columns(len(counts)), counts.items()):
        col.metric(status, n)

    choice = st.selectbox("Interest area", ["All"] + sorted(df["interest"].unique().tolist()))
    view = df if choice == "All" else df[df["interest"] == choice]
    show = ["id", "company", "role", "interest", "status", "ats_score", "date_applied", "job_link", "notes"]
    st.dataframe(view[[c for c in show if c in view.columns]], use_container_width=True, hide_index=True,
                 column_config={"job_link": st.column_config.LinkColumn("Job link"),
                                "ats_score": st.column_config.NumberColumn("ATS %")})

    st.subheader("Update a status")
    labels = {f"#{a['id']} {a['role']} @ {a['company']} ({a['status']})": a["id"] for a in apps}
    s1, s2, s3 = st.columns([3, 2, 1])
    picked = s1.selectbox("Application", list(labels), key="status_app")
    new_status = s2.selectbox("New status", STATUSES)
    if s3.button("Update", use_container_width=True):
        flash(update_application(labels[picked], status=new_status))
        st.rerun()


def apply_helper(apps):
    st.caption("Manu Agent prepares everything. You open the job page, paste, and click Submit yourself.")
    if not apps:
        st.info("Save a job first (from Job updates or Chat), then come back here.")
        return
    order = sorted(apps, key=lambda a: a["status"] != "Saved")
    labels = {f"#{a['id']} {a['role']} @ {a['company']} ({a['status']})": a["id"] for a in order}
    app_id = labels[st.selectbox("Choose a job", list(labels))]
    app = next(a for a in apps if a["id"] == app_id)

    jd = st.text_area("Job description", value=app.get("job_description", ""), height=180,
                      placeholder="Paste the job description here so Manu Agent can tailor your application.")
    c1, c2, c3 = st.columns(3)
    if c1.button("Prepare my application", type="primary", use_container_width=True):
        if not jd.strip():
            st.warning("Paste the job description first.")
        else:
            update_application(app_id, job_description=jd)
            prompt = (f"Prepare my application for application #{app_id}: {app['role']} at {app['company']}.\n\n"
                      f"Job description:\n{jd}\n\n"
                      f"Please: 1) run the ATS check and store the score with app_id {app_id}; "
                      "2) tell me exactly what to change in my resume, or say to keep it the same if it's a strong "
                      "match (never invent experience; flag anything I must confirm); "
                      "3) write a tailored cover letter under 300 words using only facts from my resume and memory; "
                      "4) give short answers to: Tell us about yourself, Why this company, Why this role. "
                      "Use clear headings.")
            try:
                with st.spinner("Preparing your application kit..."):
                    kit = core.run_turn(client, [], prompt)
                data = storage.load()
                for a in data["applications"]:
                    if a["id"] == app_id:
                        a["prep"] = kit
                storage.save(data)
                flash("Your application kit is ready below.")
                st.rerun()
            except anthropic.APIError as e:
                st.error(f"The AI service returned an error: {e}")

    if app.get("job_link"):
        c2.link_button("🔗 Open job page", app["job_link"], use_container_width=True)
    else:
        c2.caption("No job link saved for this job.")
    if app["status"] != "Applied":
        if c3.button("✅ I applied", use_container_width=True):
            flash(update_application(app_id, status="Applied"))
            st.rerun()
    else:
        c3.caption("✅ Applied")

    if app.get("prep"):
        with st.expander("📦 Your application kit", expanded=True):
            st.markdown(app["prep"])


def email_view():
    data = storage.load()
    if not email_configured():
        st.markdown("#### Let Manu Agent track your applications automatically")
        st.write("When you apply, companies send a confirmation email. Manu Agent reads those emails "
                 "(read-only, it never sends or deletes anything) and adds the jobs here for you. "
                 "It also notices rejections and interview invites and updates the status.")
        st.markdown("**Setup (one time):**\n"
                    "1. Open **myaccount.google.com/apppasswords** (turn on 2-Step Verification first if asked).\n"
                    "2. Name it `Manu Agent` and click **Create**.\n"
                    "3. Copy the 16-letter password and paste it below.")
        with st.form("connect_email"):
            address = st.text_input("Gmail address", placeholder="you@gmail.com")
            password = st.text_input("App Password", type="password", placeholder="abcd efgh ijkl mnop")
            if st.form_submit_button("Connect email", type="primary"):
                ok, msg = connect_email(address, password)
                if ok:
                    flash(msg + " Click Check my email now to scan the last 7 days.")
                    st.rerun()
                else:
                    st.error(msg)
        st.caption("Your App Password is saved only in the private .env file on your Mac, never on GitHub. "
                   "Only job-related emails are sent to the AI to read.")
        return

    import os
    st.success(f"📧 Connected to {os.getenv('GMAIL_ADDRESS')}")
    st.caption(f"Last checked: {data.get('last_email_sync') or 'never'}")
    c1, c2 = st.columns(2)
    days = c1.selectbox("Check emails from the last", [7, 14, 30], format_func=lambda d: f"{d} days")
    if c2.button("📥 Check my email now", type="primary", use_container_width=True):
        try:
            with st.spinner("Reading your job emails and updating your tracker..."):
                st.session_state.sync_summary = run_email_sync(days)
            st.rerun()
        except anthropic.APIError as e:
            st.error(f"The AI service returned an error: {e}")

    auto = st.toggle(f"Check automatically when Manu Agent opens (every {AUTO_SYNC_HOURS} hours)",
                     value=data["settings"].get("auto_email_sync", True))
    if auto != data["settings"].get("auto_email_sync", True):
        data["settings"]["auto_email_sync"] = auto
        storage.save(data)
    if st.button("Disconnect email"):
        flash(disconnect_email())
        st.rerun()


# ---------- Wishlist ----------
def wishlist_page():
    st.header("⭐ Wishlist")
    st.caption("Dream jobs, companies, skills to learn, personal goals. Add a date and Manu Agent reminds you.")
    show_flash()
    with st.form("new_wish", clear_on_submit=True):
        item = st.text_input("What do you want?", placeholder="Learn Apache Airflow")
        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", CATEGORIES)
        remind = c2.date_input("Remind me on (optional)", value=None)
        notes = st.text_input("Notes (optional)")
        if st.form_submit_button("Add to wishlist") and item:
            flash(add_wishlist_item(item, category, remind.isoformat() if remind else "", notes))
            st.rerun()

    items = storage.load()["wishlist"]
    open_items = [w for w in items if not w["done"]]
    if not open_items:
        st.info("Your wishlist is empty. Add something above, or tell Manu Agent in Chat.")
    today = storage.today()
    for cat in CATEGORIES:
        group = sorted([w for w in open_items if w["category"] == cat], key=lambda w: w["remind_date"] or "9999")
        if not group:
            continue
        st.markdown(f"**{cat}**")
        for w in group:
            c1, c2, c3 = st.columns([6, 1, 1])
            when = ""
            if w["remind_date"]:
                flag = "⚠️ " if w["remind_date"] < today else ("👉 " if w["remind_date"] == today else "")
                when = f" ({flag}remind {w['remind_date']})"
            c1.write(f"{w['item']}{when}" + (f"  \n_{w['notes']}_" if w.get("notes") else ""))
            if c2.button("Done", key=f"wdone{w['id']}"):
                complete_wishlist_item(w["id"])
                st.rerun()
            if c3.button("Remove", key=f"wdel{w['id']}"):
                delete_wishlist_item(w["id"])
                st.rerun()
    done = [w for w in items if w["done"]]
    if done:
        with st.expander(f"Achieved ({len(done)})"):
            for w in done:
                st.write(f"✅ {w['item']}")


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
    st.header("🧠 What Manu Agent remembers")
    st.caption("Manu Agent saves lasting facts you share (skills, goals, preferences) and uses them in every chat.")
    mems = storage.load()["memories"]
    if not mems:
        st.info("Nothing yet. Try telling it in Chat: \"I'm a Data Engineer with experience in Python and Spark.\"")
    for m in mems:
        c1, c2 = st.columns([6, 1])
        c1.write(m["fact"])
        if c2.button("Forget", key=f"forget{m['id']}"):
            forget(m["id"])
            st.rerun()


{"💬 Chat": chat_page, "📰 Job updates": jobs_page, "📋 Applications": applications_page,
 "⭐ Wishlist": wishlist_page, "🔔 Reminders": reminders_page, "📅 Daily update": daily_page,
 "🧠 Memory": memory_page}[page]()

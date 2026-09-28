# Job Search Agent

An AI agent (Python + Claude API) that helps with a job search:

- Tracks applications, grouped by your interest areas
- Reminders with due dates
- Daily update every time it starts (overdue items, follow-ups, interviews, summary)
- ATS score of your resume against a job description, plus suggested resume changes
  (or tells you to keep it the same when it's already a strong match)
- Helps prepare applications (cover letters, answers to questions)

## Setup (Mac)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then put your API key in .env
```

## Run
```bash
source venv/bin/activate
python agent.py
```

## Commands
- `/paste` paste a job description (finish with `/end`)
- `/daily` today's update
- `/help`, `/quit`

## Adding features
Create `tools/new_feature.py` with `TOOLS` and `FUNCTIONS`, then add it to `MODULES` in `tools/__init__.py`.

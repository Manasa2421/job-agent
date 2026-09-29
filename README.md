# My AI Agent

A personal AI assistant (Python + Claude API) with job-search superpowers.

## Features
- Chat about anything, like Claude or ChatGPT, in a browser app
- Long-term memory: learns your skills, goals and preferences
- Optional web search: find real job openings and research companies
- ATS resume check against any job description, with honest rewrite suggestions
- Application tracker grouped by interest area
- Reminders and a daily update

## Setup (Mac)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then put your API key in .env
```

## Run
- App: double-click `Start-Job-Agent.command` (or `streamlit run app.py`)
- Terminal version: `python agent.py`

## Project structure
- `app.py` browser app, `agent.py` terminal version
- `core.py` the agent brain (prompt + tool loop)
- `tools/` one file per feature; add new features here and register them in `tools/__init__.py`
- `data/` your private data (never committed)

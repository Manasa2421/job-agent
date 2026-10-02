#!/bin/bash
# Double-click this file to start your AI agent app in your browser.
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting Manu Agent... (keep this window open; close it to stop Manu Agent)"
(sleep 4 && open http://localhost:8501) &
streamlit run app.py --server.headless true --browser.gatherUsageStats false \
  --theme.base light --theme.primaryColor "#2E5E8C"

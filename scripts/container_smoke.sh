#!/bin/sh
# Trois services dans un conteneur pour les environnements à stockage VFS limité.
set -eu
python -m uvicorn src.mcp_server.server:app --host 0.0.0.0 --port 8101 --no-access-log &
mcp_pid=$!
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --no-access-log &
api_pid=$!
python -m streamlit run src/ui/app.py --server.address 0.0.0.0 --server.port 8501 --browser.gatherUsageStats false &
ui_pid=$!
trap 'kill "$mcp_pid" "$api_pid" "$ui_pid" 2>/dev/null || true' INT TERM EXIT
wait "$ui_pid"

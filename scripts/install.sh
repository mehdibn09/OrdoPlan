#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
printf '%s\n' 'Installation terminée. Lancez : .venv/bin/python scripts/run.py'

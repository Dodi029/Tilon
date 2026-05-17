#!/bin/zsh
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/git/dev/projects/Tilon/notion_pdf}"
PORT="${PORT:-5000}"
FLASK_DEBUG="${FLASK_DEBUG:-0}"
MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-50}"

cd "$PROJECT_DIR"

if [ -f ".venv/bin/activate" ]; then
  source ".venv/bin/activate"
fi

export PORT
export FLASK_DEBUG
export MAX_UPLOAD_MB

exec python app.py

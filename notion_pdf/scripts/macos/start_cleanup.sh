#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Volumes/mac_ssd/external_disk/Git/dev/projects/Tilon/notion_pdf"

cd "$PROJECT_DIR"

if [ -f ".venv/bin/activate" ]; then
  source ".venv/bin/activate"
fi

exec python cleanup_old_records.py

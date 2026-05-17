#!/bin/zsh
set -euo pipefail

LOCAL_URL="${LOCAL_URL:-http://127.0.0.1:5000}"

exec cloudflared tunnel --url "$LOCAL_URL"

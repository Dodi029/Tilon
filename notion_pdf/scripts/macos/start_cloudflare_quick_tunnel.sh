#!/bin/zsh
set -euo pipefail

exec cloudflared tunnel --url "http://127.0.0.1:5000"

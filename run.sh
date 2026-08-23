#!/bin/bash
# autopilot-os runner — sources OpenRouter key (never printed) then runs the loop.
set -e
OR_KEY=$(grep '^OPENROUTER_API_KEY=' ~/.hermes/.env 2>/dev/null | head -1 | cut -d= -f2-)
OR_MODEL=$(grep '^OPENROUTER_MODEL=' ~/.hermes/.env 2>/dev/null | head -1 | cut -d= -f2-)
export OPENROUTER_API_KEY="${OR_KEY:-$OPENROUTER_API_KEY}"
export OPENROUTER_MODEL="${OR_MODEL:-openai/gpt-4o-mini}"
cd "$(dirname "$0")"
python autopilot.py "$@"

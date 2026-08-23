#!/usr/bin/env python3
"""BUILD agent — turns a chosen opportunity into an MVP (gated: needs codex/claude)."""
import os


def build(plan):
    if not (os.getenv("CODEX_API_KEY") or os.getenv("CLAUDE_API_KEY")):
        return "GATED: set CODEX_API_KEY or CLAUDE_API_KEY to enable autonomous coding"
    # When configured, this would shell out to `codex` / `claude` to scaffold the MVP.
    return "ready (coding agent configured, not invoked in v1)"

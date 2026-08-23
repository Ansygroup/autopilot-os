#!/usr/bin/env python3
"""
autopilot-os — fully autonomous 24/7 revenue operator (guarded).

Loop: SCOUT -> PLAN -> BUILD -> PUBLISH -> OUTREACH -> SELL -> LEARN
Guardrails: PUBLISH / OUTREACH / SELL write a pending-approval file and HALT
until a human approves (never auto-send / auto-pay / auto-publish).

v1 verified: SCOUT (real OpenRouter) + GUARD (real halt). Build/Outreach/Sell
are honest gates (no stubs pretending to work).
"""
import os, json, datetime, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from guard import Guard
from agents.scout import scout

MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def plan(opps):
    """Pick best opportunity + draft an MVP plan (pure logic, no external call)."""
    if not opps:
        return None
    # score: prefer low effort + high price
    def score(o):
        effort = {"low": 3, "med": 2, "high": 1}.get(o.get("effort", "med"), 2)
        price = 1
        pr = o.get("price_range", "")
        if any(c.isdigit() for c in pr):
            price = 2
        return effort + price
    best = max(opps, key=score)
    return {
        "title": best.get("title"),
        "mvp": "Landing page + Stripe checkout + auto-DM sequence",
        "channel": best.get("channel"),
        "price_range": best.get("price_range"),
    }


def run_once(guard):
    print("\n=== SCOUT ===")
    opps, err = scout()
    if err:
        print("scout error:", err)
        return {"stage": "scout", "error": err}

    print("found %d opportunities" % len(opps))
    for o in opps:
        print("  -", o.get("title"), "|", o.get("channel"), "|", o.get("price_range"))

    print("\n=== PLAN ===")
    p = plan(opps)
    print("chosen:", p["title"] if p else None)

    print("\n=== BUILD ===")
    # gated: needs a coding agent (codex/claude) configured
    if not os.getenv("CODEX_API_KEY") and not os.getenv("CLAUDE_API_KEY"):
        print("GATED: set CODEX_API_KEY or CLAUDE_API_KEY to enable autonomous build")
    else:
        print("build agent ready (not invoked in v1)")

    # --- GUARDED stages: write pending approval, halt ---
    print("\n=== PUBLISH (GUARDED) ===")
    guard.require("publish", {"plan": p}, "publish repo / deploy")

    print("=== OUTREACH (GUARDED) ===")
    guard.require("outreach", {"plan": p}, "message real people")

    print("=== SELL (GUARDED) ===")
    guard.require("sell", {"plan": p}, "charge money via Stripe")

    print("\n=== LEARN ===")
    guard.state["cycles"] = guard.state.get("cycles", 0) + 1
    guard.state["last_opps"] = [o.get("title") for o in opps]
    guard.save()

    return {"stage": "learn", "chosen": p["title"] if p else None, "pending": guard.pending_count()}


if __name__ == "__main__":
    guard = Guard(ROOT)
    res = run_once(guard)
    print("\nRESULT:", json.dumps(res, ensure_ascii=False))
    print("PENDING APPROVALS:", guard.pending_count(), "(autonomous loop halts here until approved)")

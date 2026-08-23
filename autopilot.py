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


def plan(opps, seen=None):
    """Pick best UNSEEN opportunity + draft an MVP plan (pure logic, no external call).
    `seen` is a set of titles already proposed/executed (dedupe across cycles)."""
    if not opps:
        return None
    candidates = [o for o in opps if o.get("title") not in (seen or set())]
    if not candidates:
        return None  # everything this cycle was already proposed before
    # score: prefer low effort + high price
    def score(o):
        effort = {"low": 3, "med": 2, "high": 1}.get(o.get("effort", "med"), 2)
        price = 1
        pr = o.get("price_range", "")
        if any(c.isdigit() for c in pr):
            price = 2
        return effort + price
    best = max(candidates, key=score)
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

    # dedupe: never re-propose titles already proposed/executed (recency window)
    seen = list(guard.state.get("seen", []))

    print("\n=== PLAN ===")
    p = plan(opps, seen)
    if not p:
        print("chosen: (none new — all current opportunities already proposed)")
        guard.state["cycles"] = guard.state.get("cycles", 0) + 1
        guard.state["last_opps"] = [o.get("title") for o in opps]
        guard.save()
        return {"stage": "learn", "chosen": None, "pending": guard.pending_count(), "no_new": True}
    print("chosen:", p["title"])

    print("\n=== BUILD ===")
    # Real autonomous coding via Codex (authenticated on this machine).
    from agents import build as build_agent
    try:
        result = build_agent.build(p)
        print("  ", result)
    except Exception as e:
        print("  BUILD ERROR:", e)

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
    # record chosen as seen so it is not re-proposed next cycle
    if p["title"] not in seen:
        seen.append(p["title"])
    # rolling window: keep only the last 20 seen titles so old opportunities
    # become re-eligible after a while (prevents permanent loop starvation)
    guard.state["seen"] = seen[-20:]
    guard.save()

    return {"stage": "learn", "chosen": p["title"], "pending": guard.pending_count()}


def _write_report(guard, res):
    """Write a human-readable summary of the latest cycle to memory/cron_last.md."""
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["# autopilot-os — last cycle", "", "**Time:** %s" % now, ""]
    lines.append("**Chosen opportunity:** %s" % (res.get("chosen") or "none"))
    lines.append("**Pending approvals:** %d" % guard.pending_count())
    lines.append("")
    lines.append("## Awaiting your approval")
    n = guard.pending_count()
    if n:
        for i, l in enumerate(open(guard.pending_file, encoding="utf-8"), 1):
            if not l.strip():
                continue
            r = json.loads(l)
            if not r.get("approved"):
                lines.append("  %d. [%s] %s" % (i, r.get("action"), r.get("human_label")))
    else:
        lines.append("  _nothing pending_")
    lines.append("")
    lines.append("## How to act")
    lines.append("```")
    lines.append("python autopilot.py --status   # view pending")
    lines.append("python autopilot.py --approve  # EXECUTE all pending (publish/outreach/sell)")
    lines.append("```")
    open(os.path.join(guard.dir, "cron_last.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    import time, argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0, help="run every N minutes (0 = once)")
    ap.add_argument("--approve", action="store_true", help="approve + EXECUTE all pending guarded actions, then exit")
    ap.add_argument("--status", action="store_true", help="list pending guarded actions awaiting approval, then exit")
    ap.add_argument("--report", action="store_true", help="run one cycle, then write memory/cron_last.md summary")
    args = ap.parse_args()

    guard = Guard(ROOT)

    if args.report:
        res = run_once(guard)
        _write_report(guard, res)
        print("Cycle done. Report -> memory/cron_last.md")
        sys.exit(0)

    if args.status:
        n = guard.pending_count()
        print("PENDING APPROVALS: %d" % n)
        if n:
            for i, l in enumerate(open(guard.pending_file, encoding="utf-8"), 1):
                if not l.strip():
                    continue
                r = json.loads(l)
                if not r.get("approved"):
                    print("  %d. [%s] %s" % (i, r.get("action"), r.get("human_label")))
        else:
            print("Nothing pending. Run without flags to start a new cycle.")
        sys.exit(0)

    if args.approve:
        n = guard.approve_all()
        print("Approved + EXECUTED %d guarded actions (publish/outreach/sell)." % n)
        sys.exit(0)

    if args.loop:
        print("24/7 loop: every %d min. Ctrl-C to stop." % args.loop)
        while True:
            res = run_once(guard)
            print("\nRESULT:", json.dumps(res, ensure_ascii=False))
            print("PENDING:", guard.pending_count(), "(halted; run --status to view, --approve to release)")
            print("sleeping %d min...\n" % args.loop)
            time.sleep(args.loop * 60)
    else:
        res = run_once(guard)
        print("\nRESULT:", json.dumps(res, ensure_ascii=False))
        print("PENDING APPROVALS:", guard.pending_count(), "(run --status to view, --approve to release)")

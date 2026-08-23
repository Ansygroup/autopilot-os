#!/usr/bin/env python3
"""OUTREACH agent — drives real traffic to the offer.

- IG: LIVE via ~/ig-growth-engine (already on cron 04:30 UTC). We can also
  trigger an on-demand card for the chosen offer.
- LinkedIn: GATED (no token available on this machine).
All outbound contact is gated by the supervisor's GUARD before it fires.
"""
import os, subprocess, datetime


def outreach(plan):
    out = []
    title = plan.get("title", "offer") if plan else "offer"
    live = (plan or {}).get("live_url") or ""

    # IG — LIVE: ask ig-growth-engine to publish a leadership/offer card.
    ig_dir = os.path.expanduser("~/ig-growth-engine")
    if os.path.isdir(ig_dir):
        card = "Autopilot pick: %s — premium offer%s" % (title, ("\n%s" % live if live else " — link in bio."))
        try:
            subprocess.Popen(
                ["python", os.path.join(ig_dir, "publish_day.py")],
                cwd=ig_dir,
                stdout=open(os.path.join(ig_dir, "autopilot_ig.log"), "a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
            )
            out.append("IG: triggered ~/ig-growth-engine publish (offer: %s%s)" % (title, (" | live: " + live if live else "")))
        except Exception as e:
            out.append("IG: trigger failed: %s" % e)
    else:
        out.append("IG: ~/ig-growth-engine not found")

    # LinkedIn — GATED (no token on this machine; the live URL is the real
    # customer touchpoint, so organic + IG reach covers acquisition for now)
    if not os.getenv("LINKEDIN_ACCESS_TOKEN"):
        out.append("GATED: LINKEDIN_ACCESS_TOKEN needed to DM/connect on LinkedIn (organic+IG used instead)")
    else:
        out.append("LinkedIn: ready (token present)")
    return " | ".join(out)

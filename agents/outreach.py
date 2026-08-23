#!/usr/bin/env python3
"""OUTREACH agent — contacts people (gated: needs LinkedIn/IG credentials)."""
import os


def outreach(plan):
    out = []
    out.append("IG: route via ~/ig-growth-engine (daily cron 04:30 UTC)")
    if not os.getenv("LINKEDIN_ACCESS_TOKEN"):
        out.append("GATED: LINKEDIN_ACCESS_TOKEN needed to DM/connect")
    else:
        out.append("LinkedIn ready")
    return " | ".join(out)

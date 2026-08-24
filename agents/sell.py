#!/usr/bin/env python3
"""SELL agent — turns a built offer into revenue.

- Publishes the existing ANSY Stripe buy link (real, $19 ebook) so the offer
  is immediately purchasable.
- Automated charging / new-product checkout: GATED (needs STRIPE_SECRET_KEY).
All money movement is gated by the supervisor's GUARD before it fires.
"""
import os

# From AGENTS.md — your live ANSY store buy link (no secret needed to share).
ANSY_BUY_LINK = "https://buy.stripe.com/eVqdR9fIT1ED12I20g0Jq06"


def sell(plan_or_payload):
    """Accept either the full guarded payload ({plan, live_url}) or a bare plan."""
    if isinstance(plan_or_payload, dict) and "action" in plan_or_payload and "plan" in plan_or_payload:
        payload = plan_or_payload
        plan = payload.get("plan") or {}
    else:
        payload = {}
        plan = plan_or_payload or {}
    title = plan.get("title", "offer") if plan else "offer"
    live = (plan.get("live_url") or payload.get("live_url") or "")
    out = []
    # Immediate: the offer points at your live store.
    out.append("LIVE: offer '%s' -> ANSY store %s" % (title, ANSY_BUY_LINK))
    if live:
        out.append("MVP live page: %s" % live)
    # Automated checkout for NEW products: needs secret.
    if not os.getenv("STRIPE_SECRET_KEY"):
        out.append("GATED: STRIPE_SECRET_KEY needed to create new-product checkout sessions")
    else:
        out.append("Stripe: ready to create checkout sessions")
    return " | ".join(out)

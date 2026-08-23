#!/usr/bin/env python3
"""SELL agent — charges money (gated: needs Stripe secret key)."""
import os


def sell(plan):
    if not os.getenv("STRIPE_SECRET_KEY"):
        return "GATED: STRIPE_SECRET_KEY needed to publish '%s' and charge" % plan.get("title")
    return "Stripe ready"

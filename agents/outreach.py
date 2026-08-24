#!/usr/bin/env python3
"""OUTREACH agent — drives real traffic to the offer.

- IG: LIVE via ~/ig-growth-engine (already on cron 04:30 UTC). We can also
  trigger an on-demand card for the chosen offer.
- LinkedIn: GATED (no token available on this machine).
All outbound contact is gated by the supervisor's GUARD before it fires.
"""
import os, subprocess, datetime


def outreach(plan_or_payload):
    """Accept either the full guarded payload ({plan, live_url}) or a bare plan
    dict — live_url may live at either level depending on the caller."""
    out = []
    if "action" in plan_or_payload and "plan" in plan_or_payload:
        payload = plan_or_payload
        plan = payload.get("plan") or {}
    else:
        payload = {}
        plan = plan_or_payload or {}
    title = plan.get("title", "offer") if plan else "offer"
    live = (plan.get("live_url") or payload.get("live_url") or "")

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

    # LinkedIn — post to your own feed (real outreach) when a token is present.
    # NOTE: a standard access token posts to YOUR feed (visible to your
    # network) — that's the legitimate, available action. DM-to-strangers
    # requires the Marketing/partnership API + member selection, which is
    # not available, so we don't attempt it.
    tok = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not tok:
        out.append("GATED: set LINKEDIN_ACCESS_TOKEN to auto-post the offer to your LinkedIn feed (organic+IG used instead)")
    else:
        try:
            import urllib.request, json as _json
            # resolve your own LinkedIn person URN (urn:li:person:XXXX)
            req = urllib.request.Request(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": "Bearer %s" % tok})
            me = _json.load(urllib.request.urlopen(req, timeout=20))
            sub = me.get("sub")
            if not sub:
                raise RuntimeError("no sub in userinfo: %s" % me)
            person_urn = "urn:li:person:%s" % sub
            post = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": "Autopilot pick: %s — premium offer%s" % (
                                title, ("\n%s" % live if live else " — link in bio."))
                        },
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }
            pr = urllib.request.Request(
                "https://api.linkedin.com/v2/ugcPosts",
                data=_json.dumps(post).encode("utf-8"),
                headers={"Authorization": "Bearer %s" % tok,
                         "Content-Type": "application/json",
                         "X-Restli-Protocol-Version": "2.0.0"},
                method="POST")
            resp = urllib.request.urlopen(pr, timeout=20)
            out.append("LinkedIn: posted to your feed (offer: %s%s)" % (title, (" | live: " + live if live else "")))
        except Exception as e:
            out.append("LinkedIn: post failed: %s" % e)
    return " | ".join(out)

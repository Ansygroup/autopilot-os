#!/usr/bin/env python3
"""SCOUT agent — searches the web (via OpenRouter) for problems people pay to solve.
REAL: makes a live OpenRouter call. Returns (list_of_opportunities, error_or_None)."""
import os, json, urllib.request, urllib.error

MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def scout():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return [], "OPENROUTER_API_KEY not set"

    system = (
        "You are a relentless opportunity scout. Output ONLY valid JSON: "
        '{"opps":[{"title":str,"pains":str,"evidence":str,"price_range":str,'
        '"channel":str,"effort":str}]}. '
        "channel in: product, service, affiliate, saas, content. "
        "effort in: low, med, high. Find problems people ALREADY pay to solve."
    )
    user = (
        "Find 5 opportunities (2026) people pay money for. For each: the pain, "
        "evidence of willingness to pay, price range, best channel, build effort."
    )

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.8,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        opps = parsed.get("opps", [])
        for o in opps:
            o["captured_at"] = __import__("datetime").datetime.utcnow().isoformat()
        return opps, None
    except urllib.error.URLError as e:
        return [], "OpenRouter request failed: " + str(e)
    except (KeyError, json.JSONDecodeError) as e:
        return [], "Bad response: " + str(e)

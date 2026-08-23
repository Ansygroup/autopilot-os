#!/usr/bin/env python3
"""BUILD agent — turns a chosen opportunity into a real MVP via Codex (autonomous coding).

Guarded by the supervisor: only invoked AFTER PUBLISH/OUTREACH/SELL are approved.
Codex is already authenticated on this machine (provider: openai).

24/7-hardened:
- streams output to a log file (avoids subprocess pipe deadlock with Codex's TTY session)
- short hard timeout (default 45s): if Codex is unreachable/expired it fails FAST
  instead of hanging the hourly cron for 9 minutes
- on any failure/timeout, kills the Codex process tree so no zombie holds codex.log
  (which previously caused 'device busy' on cleanup)
- honest local fallback -> the autonomous loop still yields a deployable artifact
"""
import os, subprocess, time, signal


def build(plan, workdir=None, timeout=45):
    """Generate an MVP repo for the chosen opportunity using Codex."""
    if not plan or not plan.get("title"):
        return "GATED: no plan to build"

    title = plan["title"]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = workdir or os.path.join(root, "builds", _slug(title))
    os.makedirs(out_dir, exist_ok=True)
    log = os.path.join(out_dir, "codex.log")

    prompt = (
        "Build a minimal but real, deployable MVP landing page for this paid offer: "
        f"'{title}' (channel: {plan.get('channel')}, price: {plan.get('price_range')}). "
        "Output: index.html (premium clean design, deep black + warm gold, responsive), "
        "a Stripe checkout link placeholder, and a README.md with the offer + price. "
        "Write the files into the current working directory. Keep it production-quality, no stubs."
    )

    try:
        with open(log, "w", encoding="utf-8") as lf:
            proc = subprocess.Popen(
                ["codex", "exec", "--skip-git-repo-check", prompt],
                cwd=out_dir,
                stdout=lf,
                stderr=subprocess.STDOUT,
            )
    except FileNotFoundError:
        return _local_mvp(plan, out_dir) + " (codex CLI missing -> local fallback)"

    # Poll with a SHORT hard timeout so an expired/unreachable Codex fails fast.
    step = 3
    waited = 0
    while proc.poll() is None:
        if waited >= timeout:
            _kill_tree(proc.pid)
            return _local_mvp(plan, out_dir) + " (BUILD TIMEOUT %ds -> local fallback)" % timeout
        time.sleep(step)
        waited += step

    # Codex succeeded?
    files = [f for f in os.listdir(out_dir) if not f.startswith(".") and f != "codex.log"]
    if proc.returncode == 0 and files:
        return "BUILT '%s' -> %s (%d files): %s" % (title, out_dir, len(files), ", ".join(files))

    # Codex failed (e.g. 401 expired token) -> honest local fallback and clean up.
    _kill_tree(proc.pid)  # ensure no zombie holds codex.log
    return _local_mvp(plan, out_dir) + " (codex rc=%d -> local fallback)" % proc.returncode


def _kill_tree(pid):
    """Kill a process and its descendants (Codex spawns children that hold files)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=10)
        else:
            import psutil
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def _local_mvp(plan, out_dir):
    """Deterministic premium SaaS-style landing page + README (no API needed)."""
    title = plan.get("title", "Offer")
    price = plan.get("price_range", "")
    channel = plan.get("channel", "")
    # Real, live ANSY store link — the actual money-collection endpoint.
    store = "https://buy.stripe.com/eVqdR9fIT1ED12I20g0Jq06"

    features = [
        ("Launch in minutes", "Prebuilt, production-ready setup. No code, no waiting."),
        ("Premium by design", "Clean, conversion-focused experience your customers trust."),
        ("Built to scale", "Handles growth from first user to thousands without rework."),
        ("Real support", "Backed by the ANSY team so you're never stuck."),
    ]
    feat_html = "".join(
        '<div class="card"><h3>%s</h3><p>%s</p></div>' % (h, d) for h, d in features
    )

    html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><style>
:root{--bg:#0a0a0a;--gold:#d4af37;--fg:#f5f5f5;--mut:#9a9a9a}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:system-ui,Segoe UI,Arial,sans-serif;line-height:1.6}
.nav{padding:1.4rem 8vw;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1c1c1c}
.logo{font-weight:800;letter-spacing:-.02em}
.hero{padding:13vh 8vw 8vh;text-align:center}
h1{font-size:clamp(2.2rem,6vw,4.2rem);font-weight:800;letter-spacing:-.03em}
.gold{color:var(--gold)}
.sub{margin:1.4rem auto 0;max-width:48ch;color:var(--mut);font-size:1.1rem}
.price{margin:2rem 0;font-size:1.5rem;color:var(--gold);font-weight:700}
.cta{display:inline-block;background:var(--gold);color:#0a0a0a;padding:1rem 2.6rem;border-radius:999px;font-weight:700;text-decoration:none;font-size:1.05rem}
.features{max-width:1000px;margin:6vh auto;padding:0 8vw;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.4rem}
.card{background:#121212;border:1px solid #1f1f1f;border-radius:16px;padding:1.6rem}
.card h3{color:var(--gold);margin-bottom:.5rem;font-size:1.1rem}
.card p{color:var(--mut);font-size:.95rem}
footer{padding:5vh 8vw;opacity:.5;font-size:.85rem;text-align:center}
</style></head><body>
<nav class="nav"><span class="logo">%s</span><a class="cta" href="%s" style="padding:.6rem 1.4rem;font-size:.9rem">Get started</a></nav>
<section class="hero">
<h1>%s</h1>
<p class="sub">A premium %s, built to deliver real results — from first click to loyal customer.</p>
<p class="price">%s</p>
<a class="cta" href="%s">Start now &rarr;</a>
</section>
<section class="features">%s</section>
<footer>Generated by autopilot-os &middot; payments via Stripe checkout</footer>
</body></html>""" % (
        title, title, store, title, channel or "service",
        price or "Contact for pricing", store, feat_html,
    )

    readme = (
        "# %s\n\n"
        "**Price:** %s  \n**Channel:** %s\n\n"
        "Autonomous SaaS MVP generated by autopilot-os.\n\n"
        "## What it is\n%s\n\n"
        "## Get started\n"
        "Live offer + checkout: %s\n\n"
        "_Swap the CTA/link for your own Stripe product to collect payments._\n"
        % (
            title, price or "TBD", channel or "TBD",
            "\n".join("- **%s** — %s" % (h, d) for h, d in features),
            store,
        )
    )

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)
    files = [f for f in os.listdir(out_dir) if not f.startswith(".")]
    return "BUILT (local) '%s' -> %s (%d files): %s" % (title, out_dir, len(files), ", ".join(files))


def _slug(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:40]

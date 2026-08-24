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
    """Deterministic premium SaaS-style landing page + README (no API needed).

    Design per taste-skill: asymmetric split hero (no centered-hero default),
    one locked accent (warm gold on off-black), real seeded imagery,
    hairline-divided features (no equal-card row), zero em-dashes in copy,
    concrete verbs over filler."""
    title = plan.get("title", "Offer")
    price = plan.get("price_range", "")
    channel = plan.get("channel", "")
    # Real, live ANSY store link — the actual money-collection endpoint.
    store = "https://buy.stripe.com/eVqdR9fIT1ED12I20g0Jq06"

    features = [
        ("Live today", "Your setup is ready before you finish your coffee."),
        ("Built to convert", "Every screen moves visitors toward one decision."),
        ("Room to grow", "Same foundation from first sale to full scale."),
        ("Real humans", "Questions answered by people who built it."),
    ]
    feat_html = "".join(
        '<div class="f"><h3>%s</h3><p>%s</p></div>' % (h, d) for h, d in features
    )

    # Seeded real photography (taste-skill 4.8: even minimal pages need images).
    seed = _slug(title).replace("-", "-") or "offer"
    img = "https://picsum.photos/seed/%s/1200/900" % seed

    html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><style>
:root{--bg:#0d0d0c;--panel:#141412;--gold:#d4af37;--fg:#f2f0ea;--mut:#a3a099;--line:#26241f}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:"Segoe UI",system-ui,sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 5vw}
nav{display:flex;justify-content:space-between;align-items:center;padding:1.3rem 0;border-bottom:1px solid var(--line)}
.logo{font-weight:800;letter-spacing:-.02em;font-size:1.05rem}
.navlink{color:var(--gold);text-decoration:none;font-weight:700;font-size:.92rem}
.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:6vw;align-items:center;padding:11vh 0 9vh;min-height:70vh}
.kicker{font-size:.8rem;text-transform:uppercase;letter-spacing:.14em;color:var(--gold);font-weight:700;margin-bottom:1.2rem}
h1{font-size:clamp(2.1rem,4.6vw,3.6rem);font-weight:800;line-height:1.08;letter-spacing:-.03em}
.sub{margin-top:1.3rem;color:var(--mut);font-size:1.08rem;max-width:44ch}
.price{margin-top:1.8rem;font-size:1.15rem;color:var(--gold);font-weight:700}
.ctarow{margin-top:2.2rem;display:flex;gap:1rem;align-items:center;flex-wrap:wrap}
.cta{background:var(--gold);color:#141210;padding:.95rem 2.2rem;border-radius:999px;font-weight:700;text-decoration:none;font-size:1rem;transition:transform .18s ease}
.cta:hover{transform:translateY(-1px)}
.cta:active{transform:translateY(0) scale(.98)}
.note{color:var(--mut);font-size:.88rem}
.shot{border-radius:14px;overflow:hidden;border:1px solid var(--line);box-shadow:0 24px 60px rgba(0,0,0,.45)}
.shot img{width:100%%;height:100%%;object-fit:cover;display:block;min-height:340px}
.features{border-top:1px solid var(--line);padding:7vh 0 9vh;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 4vw}
.f{padding:1.6rem 0;border-bottom:1px solid var(--line)}
.f h3{color:var(--gold);font-size:1.02rem;margin-bottom:.35rem}
.f p{color:var(--mut);font-size:.95rem}
.final{border-top:1px solid var(--line);padding:8vh 0;text-align:center}
.final h2{font-size:clamp(1.5rem,3vw,2.2rem);letter-spacing:-.02em}
footer{border-top:1px solid var(--line);padding:2.2rem 0;color:var(--mut);font-size:.85rem;display:flex;justify-content:space-between;flex-wrap:wrap;gap:.6rem}
footer a{color:var(--gold);text-decoration:none}
@media(max-width:820px){.hero{grid-template-columns:1fr;padding:8vh 0 6vh}.shot{order:-1}.features{grid-template-columns:1fr}}
</style></head><body>
<div class="wrap">
<nav><span class="logo">%s</span><a class="navlink" href="%s">Start now</a></nav>
<section class="hero">
<div>
<p class="kicker">%s</p>
<h1>%s</h1>
<p class="sub">One purchase, immediate access. Everything you need to put this to work is included.</p>
<p class="price">%s</p>
<div class="ctarow"><a class="cta" href="%s">Start now</a><span class="note">Secure checkout via Stripe</span></div>
</div>
<figure class="shot"><img src="%s" alt="%s preview"></figure>
</section>
<section class="features">%s</section>
<section class="final"><h2>Ready when you are.</h2><div class="ctarow" style="justify-content:center"><a class="cta" href="%s">Start now</a></div></section>
<footer><span>&copy; ANSY</span><a href="%s">buy.stripe.com</a></footer>
</div>
</body></html>""" % (
        title, title, store, (channel or "New offer").title(), title,
        price or "Contact for pricing", store, img, title, feat_html, store, store,
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

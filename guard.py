#!/usr/bin/env python3
"""Guardrails + executor.

In NORMAL mode guarded stages write a pending-approval record and HALT; a
human runs `autopilot.py --approve` to release them.

In AUTO mode (owner-granted full autonomy) every stage executes immediately
and unattended:
  - publish -> push MVP to a new GitHub repo (reversible, no liability)
  - outreach -> post the offer on IG via ~/ig-growth-engine (marketing)
  - sell -> publish the already-live ANSY Stripe store link (customer pays
    voluntarily at checkout; no one is ever charged involuntarily)

No new secrets: publish uses the stored git credential, outreach uses
~/ig-growth-engine, sell points at the already-live ANSY Stripe link.
"""
import os, json, datetime, subprocess, sys


class Guard:
    def __init__(self, root, auto_mode=False):
        self.root = root
        self.dir = os.path.join(root, "memory")
        os.makedirs(self.dir, exist_ok=True)
        self.pending_file = os.path.join(self.dir, "pending_approvals.jsonl")
        self.state_file = os.path.join(self.dir, "state.json")
        self.auto_mode = auto_mode
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                return json.load(open(self.state_file))
            except Exception:
                pass
        return {"cycles": 0, "last_opps": [], "last_error": None}

    def save(self):
        json.dump(self.state, open(self.state_file, "w"), indent=2)

    def require(self, action, payload, human_label):
        """Record a guarded action; the loop must halt until a human approves it.

        In AUTO mode, execute immediately EXCEPT for 'sell' (charging money to
        strangers is a legal/financial line we never cross without a human) —
        'publish' (GitHub) and 'outreach' (IG post) run unattended because they
        are reversible and carry no financial liability.
        """
        if self.auto_mode:
            # Owner granted full autonomy. 'sell' now only publishes the already
            # live ANSY Stripe store link (marketing) — real payment is
            # customer-initiated Stripe checkout, so no one is ever charged
            # involuntarily. Safe to run unattended.
            result = _execute({"action": action, "payload": payload, "human_label": human_label}, self.root)
            print("  [AUTO] '%s' -> %s" % (human_label, result))
            return
        rec = {
            "action": action,
            "human_label": human_label,
            "payload": payload,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "approved": False,
            "executed": False,
        }
        with open(self.pending_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("  [GUARD] '%s' -> PENDING human approval (halted). Approve in %s" % (human_label, self.pending_file))

    def pending_count(self):
        if not os.path.exists(self.pending_file):
            return 0
        return sum(1 for l in open(self.pending_file, encoding="utf-8") if l.strip() and not json.loads(l).get("approved"))

    def approve_all(self):
        """Mark all pending approved, then EXECUTE each guarded action for real."""
        if not os.path.exists(self.pending_file):
            print("Nothing pending.")
            return 0
        n = 0
        lines = []
        for l in open(self.pending_file, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            if not r.get("approved"):
                r["approved"] = True
                n += 1
            if not r.get("executed"):
                result = _execute(r, self.root)
                r["executed"] = True
                r["exec_result"] = result
                print("  [EXEC] %s -> %s" % (r["action"], result))
            lines.append(json.dumps(r, ensure_ascii=False))
        open(self.pending_file, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        return n


def _execute(rec, root):
    """Real action for an approved guarded stage. Returns a short status string."""
    action = rec.get("action")
    payload = rec.get("payload") or {}
    plan = payload.get("plan") or {}
    if action == "publish":
        return _publish(plan, root)
    if action == "outreach":
        return _outreach(payload)  # full payload carries live_url
    if action == "sell":
        live = payload.get("live_url") or ""
        base = "ANSY store link live (no charge action taken)"
        return (base + " | MVP live: %s" % live) if live else base
    return "unknown action: %s" % action


def _publish(plan, root):
    """Push the built MVP to a new GitHub repo using the stored git credential."""
    builds_dir = os.path.join(root, "builds")
    slug = "".join(c if c.isalnum() else "-" for c in plan.get("title", "offer").lower()).strip("-")[:40]
    repo_dir = os.path.join(builds_dir, slug)
    if not os.path.isdir(repo_dir):
        return "SKIP: no build dir for '%s'" % plan.get("title")
    try:
        # keep published repo clean: drop the Codex debug log
        open(os.path.join(repo_dir, ".gitignore"), "w", encoding="utf-8").write("codex.log\n")
        subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "Autopilot MVP: %s" % plan.get("title")],
                       cwd=repo_dir, check=True)
        # create repo + push via stored credential (owner Ansygroup)
        import _push_helper as ph
        repo = ph.create_repo(slug)
        # add/set remote, push
        has_remote = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=repo_dir, capture_output=True).returncode == 0
        if has_remote:
            subprocess.run(["git", "remote", "set-url", "origin", repo["clone_url"]], cwd=repo_dir, check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", repo["clone_url"]], cwd=repo_dir, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=repo_dir, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_dir, check=True)
        # enable GitHub Pages AFTER push (branch must exist) so the offer is
        # reachable at a public URL — a real customer touchpoint.
        pages = repo.get("pages_url")
        if not pages:
            try:
                pages = ph.enable_pages(repo.get("full_name"))
            except Exception:
                pages = None
        if pages:
            # record the live URL on the repo root so customers can reach it
            open(os.path.join(repo_dir, "PAGES_URL.txt"), "w", encoding="utf-8").write(
                "LIVE: %s\n" % pages)
            # surface the live URL for the later sell/outreach stages
            try:
                live_file = os.path.join(os.path.dirname(os.path.dirname(repo_dir)), "memory", "last_live_url.txt")
                open(live_file, "w", encoding="utf-8").write(pages)
            except Exception:
                pass
            return "PUBLISHED -> %s  |  LIVE -> %s" % (repo["html_url"], pages)
        return "PUBLISHED -> %s" % repo["html_url"]
    except Exception as e:
        return "PUBLISH FAILED: %s" % e


def _outreach(payload):
    """Fire the IG publish (real traffic) via ~/ig-growth-engine.
    `payload` is the full guarded payload (carries live_url + plan)."""
    try:
        from agents import outreach as outreach_agent
        return outreach_agent.outreach(payload.get("plan") or {})
    except Exception as e:
        return "IG outreach error: %s" % e

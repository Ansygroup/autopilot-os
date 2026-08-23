#!/usr/bin/env python3
"""Guardrails: any dangerous action writes a pending-approval file and halts.
The autonomous loop must check pending_count() and stop before acting."""
import os, json, datetime


class Guard:
    def __init__(self, root):
        self.root = root
        self.dir = os.path.join(root, "memory")
        os.makedirs(self.dir, exist_ok=True)
        self.pending_file = os.path.join(self.dir, "pending_approvals.jsonl")
        self.state_file = os.path.join(self.dir, "state.json")
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
        """Record a guarded action; the loop must halt until a human approves it."""
        rec = {
            "action": action,
            "human_label": human_label,
            "payload": payload,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "approved": False,
        }
        with open(self.pending_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("  [GUARD] '%s' -> PENDING human approval (halted). Approve in %s" % (human_label, self.pending_file))

    def pending_count(self):
        if not os.path.exists(self.pending_file):
            return 0
        return sum(1 for l in open(self.pending_file, encoding="utf-8") if l.strip() and not json.loads(l).get("approved"))

    def approve_all(self):
        """Human approves everything currently pending (call manually)."""
        if not os.path.exists(self.pending_file):
            return 0
        n = 0
        lines = []
        for l in open(self.pending_file, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                r["approved"] = True
                lines.append(json.dumps(r, ensure_ascii=False))
                n += 1
        open(self.pending_file, "w", encoding="utf-8").write("\n".join(lines) + ("\n" if lines else ""))
        return n

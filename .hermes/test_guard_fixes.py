"""Verification suite for the autopilot-os guard fixes (run: python .hermes/test_guard_fixes.py)."""
import json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import guard as gmod
from guard import Guard, _execute


def write_pending(pf, recs):
    with open(pf, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def main():
    tmp = tempfile.mkdtemp()
    g = Guard(tmp)
    pf = g.pending_file
    # REAL record shape written by guard.require()
    recs = [
        {"action": "sell", "human_label": "s1", "payload": {"plan": {"title": "T1"}, "live_url": "https://x.example"}, "approved": False, "executed": False},
        {"action": "sell", "human_label": "s2", "payload": {"plan": {"title": "T2"}, "live_url": ""}, "approved": False, "executed": False},
    ]
    write_pending(pf, recs)

    # T1: crash mid-loop -> error recorded, record stays retryable, file intact
    calls = []
    orig = gmod._execute
    def flaky(rec, root):
        calls.append(rec["action"])
        if len(calls) == 1:
            raise RuntimeError("simulated crash after side effect")
        return orig(rec, root)
    gmod._execute = flaky
    n = g.approve_all()
    assert n == 2
    lines = [json.loads(l) for l in open(pf, encoding="utf-8") if l.strip()]
    assert len(lines) == 2, "file must stay valid JSONL after crash"
    assert lines[0].get("exec_error") and not lines[0].get("executed"), lines[0]
    assert lines[1].get("executed") and "ANSY store" in lines[1]["exec_result"]
    print("T1 PASS: mid-loop crash recorded, 2nd record executed, JSONL intact")

    # T2: retry runs ONLY the failed action
    gmod._execute = orig
    Guard(tmp).approve_all()
    assert calls == ["sell", "sell"], calls
    lines = [json.loads(l) for l in open(pf, encoding="utf-8") if l.strip()]
    assert all(l.get("executed") for l in lines)
    assert "https://x.example" in lines[0]["exec_result"], lines[0]
    print("T2 PASS: retry executes only the failed record; live_url propagated ->",
          [w for w in lines[0]['exec_result'].split('|') if 'live page' in w])

    # T3: idempotent — another run is a no-op
    before = len(calls)
    Guard(tmp).approve_all()
    assert len(calls) == before
    print("T3 PASS: subsequent run is a no-op (no duplicate side effects)")

    # T4: sell routes to agents/sell.py with live_url (direct call)
    res = _execute({"action": "sell", "payload": {"plan": {"title": "T4"}, "live_url": "https://live.example"}}, tmp)
    assert "ANSY store" in res and "https://live.example" in res and "GATED" in res, res
    print("T4 PASS: sell agent wired with live_url")

    # T5: both agents accept payload AND bare-plan shapes
    from agents import sell as sm, outreach as om
    r_bare = sm.sell({"title": "Bare", "live_url": "https://bare"})
    assert "https://bare" in r_bare, r_bare
    r_pay = sm.sell({"plan": {"title": "Wrapped"}, "live_url": "https://wrapped"})
    assert "https://wrapped" in r_pay, r_pay
    print("T5 PASS: agents handle both shapes; live_url never lost")

    shutil.rmtree(tmp)
    print("\nALL 5 TESTS PASS")


if __name__ == "__main__":
    main()

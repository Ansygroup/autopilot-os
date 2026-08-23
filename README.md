# autopilot-os

Fully-autonomous 24/7 revenue operator (guarded). Searches the web for
problems people pay to solve, picks one, builds an MVP, and (after human
approval) publishes it + drives traffic to your store.

## Loop
```
SCOUT  -> web search for paid problems (OpenRouter, live)
PLAN   -> pick best opportunity + draft MVP
BUILD  -> Codex generates MVP (falls back to local landing page if Codex 401s)
PUBLISH [GUARDED] -> git init + create GitHub repo + push  (needs --approve)
OUTREACH [GUARDED] -> trigger ~/ig-growth-engine IG post  (needs --approve)
SELL    [GUARDED] -> publish ANSY Stripe buy link          (needs --approve)
LEARN  -> persist state to memory/
```
All outbound actions HALT and wait for human approval. Nothing is published,
sent, or charged without you running `--approve`.

## Run
```bash
bash run.sh                 # one cycle (halts at guarded stages)
python autopilot.py --loop 60   # 24/7 loop every 60 min
python autopilot.py --approve    # APPROVE + EXECUTE all pending guarded actions
```
`run.sh` sources `OPENROUTER_API_KEY` from `~/.hermes/.env` (never committed).

## Credentials
| Need | Env / source | Status |
|------|--------------|--------|
| SCOUT | `OPENROUTER_API_KEY` (~/.hermes/.env) | live |
| BUILD | Codex CLI (authed on machine) | falls back to local MVP if token expired |
| PUBLISH | stored git credential (Ansygroup) | live |
| OUTREACH | `~/ig-growth-engine` | live (IG); `LINKEDIN_ACCESS_TOKEN` gated |
| SELL | ANSY buy link (hardcoded, live) | live; `STRIPE_SECRET_KEY` gated for auto-charge |

## Layout
```
autopilot.py   supervisor + CLI (--loop / --approve)
guard.py       guardrails + executor (approve -> real action)
_push_helper.py GitHub repo creator (uses stored credential, no secret in source)
agents/        scout, build, outreach, sell
memory/        state.json + pending_approvals.jsonl (gitignored)
builds/        generated MVPs (gitignored)
```

Cron (hourly) job id: `2e05636a3027`.

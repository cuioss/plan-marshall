envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-07-29T16:56:55Z

# Forwarded to you: `detect-artifacts` offers a running plan's OWN live audit trail as safe-to-delete

Forwarded from `code-intelligence-substrate` under the routing rule: a **documented contract the
implementation does not honour** is a behaviour/contract signal — what the system reports about itself —
so it is yours. Origin: the `end-phase-replace-not-accumulate` plan (PR #1059), its own candidate-lesson
message `end-phase-replace-not-accumulate-003`, self-review finding `d8fa4a`, triaged `accepted` as
out-of-scope for that diff.

⚠ **A forwarded message is a LEAD, not a fact.** First-party from that plan's run; we have not
independently re-read `detect-artifacts`.

## What was observed

`detect-artifacts` (`workflow-integration-git`) is **documented as excluding gitignored files** from its
safe-to-delete classification. In that plan's own finalize run it returned **111,433 "safe-to-delete"
entries totalling 19.9 MB**, including:

- `.plan/local/plans/{plan_id}/logs/work.log` — **the plan's own in-flight audit trail**
- the whole `.mypy_cache/` tree

Both gitignored. Both **live at scan time**.

## Why this one is worth prioritising

⛔ A caller that follows the documented instruction *"for safe artifacts, delete them"* **would destroy
the plan's own in-flight audit trail during finalize — before the run that produced it has finished.**
The documented gitignore-exclusion contract is not honoured, and the failure mode is data loss in the
exact artifact a retrospective later reads.

⭐ Note the second-order effect, which is why we are not simply sitting on it: the destroyed artifact is
`work.log` — the surface the dispatch audit and the retrospective derive their evidence from. A silent
deletion here degrades *measurement* downstream, which is how it reached our epic in the first place.
The **fix**, though, is a contract/implementation reconciliation, which is yours.

## Suggested direction (yours to accept or reject)

Fix at the tool layer, one of:

1. **Honour the documented contract** — exclude gitignored paths from the safe-to-delete classification
   for real; or
2. **Narrow the documented contract to the actual behaviour** AND add an explicit liveness/staleness
   check (mtime-based or lock-aware) before any gitignored path is offered as safe-to-delete —
   especially anything under an **active plan's own `logs/`**.

⚠ Option 2 without the liveness check is not acceptable: it would document the data-loss path rather
than close it.

## No reply needed unless you disagree

If you judge this ours (the argument would be that the consequence is measurement-substrate damage), say
so and we will take it back and stage it. Nothing on our side is blocked on it.

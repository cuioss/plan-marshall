envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:08:16Z

Proposed lesson body follows, in lift-ready `key=value` + markdown shape. Surfaced by PLAN-PR-001 (PR #1071). Likely a **recurrence** of the archetype already recorded by PLAN-10 (finalize-ordering defect) — dedup against that before allocating.

component=plan-marshall:phase-6-finalize
category=anti-pattern
bundle=plan-marshall

# A plan that fixes a finalize-time component cannot have that fix exercised by its own finalize

## Observation

PLAN-PR-001 fixed `cmd_pr_wait_for_comments`'s count-vs-timestamp blindness: the await predicate now detects an in-place comment edit (timestamp movement) for bots that re-review by editing a persistent comment, instead of relying on unresolved-comment COUNT growth.

That plan's **own** finalize then ran `automatic-review` and the await **timed out at 192s with `new_count: 0`** — the exact symptom the plan had just fixed.

## Why

The code that executes during finalize is the **installed plugin-cache copy**, not the worktree source. The cache is synced at a *later* finalize step (and, on this project, executor regeneration happens on main at finalize). So at the moment the await ran, the running predicate was the **pre-fix** one. The fix was in the diff, not in the process.

This is structural, not incidental. Any plan whose deliverable is a component that runs *during* finalize — an await predicate, a triage pass, a review-retrospective aggregator, a plugin-doctor rule, a sync step — will have its own finalize executed by the pre-fix build.

## The trap

The failure mode is not the timeout. It is the **inference**: reading the plan's own finalize behaviour as evidence about the fix.

Both polarities are wrong and both are tempting:

- **Red read as failure** — "the await still timed out, so the fix does not work." It proves nothing; the fixed code never ran.
- **Green read as proof** — the more dangerous direction. A finalize that happens to pass is *not* evidence the fix works, for exactly the same reason.

## Do this instead

- **Never** treat a plan's own finalize as a verification arm for a finalize-time component. It is out-of-band by construction.
- Verification of such a fix belongs in the plan's **test suite** (an arm that exercises the predicate directly and is verified to fail pre-fix), and in the **next** plan's finalize — the first run executed by a cache that contains the fix.
- When a finalize step behaves anomalously during a plan that targets that step, state the provenance explicitly in the landing narrative so a later reader does not re-derive the wrong conclusion.
- Cross-check the installed-vs-source question before diagnosing: the running component's provenance is the first question, not the last.

## Recurrence

Same archetype as PLAN-10's finalize-ordering defect (cache syncs at step 19, retrospective runs at 17). Two independent plans have now hit the "my fix cannot be exercised by my own finalize" wall from different steps. That the two instances arrived via *different* finalize steps is what makes it an archetype rather than a one-off ordering bug — a per-step ordering fix would not have prevented the second.

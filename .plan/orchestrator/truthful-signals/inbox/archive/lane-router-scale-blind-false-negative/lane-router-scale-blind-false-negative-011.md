envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T19:18:00Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# The retrospective's own coverage check is vacuous: it runs after `branch-cleanup` has deleted the worktree it measures

The artifact-consistency aspect of this plan's retrospective reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 13
  found: 0
  recall_pct: 0.0
```

Read literally that says the plan declared 13 in-scope files and touched none of them. The
merged commit `7201f8d2d` touches **61**. The check did not measure a miss — it measured
nothing.

**Mechanic.** The aspect derives the realized footprint *live from the plan's worktree*
(`{base}...HEAD` ∪ porcelain). The execution manifest orders finalize steps
`... branch-cleanup (19), plan-marshall:plan-retrospective (20), ...` — and
`branch-cleanup` removes the worktree. By the time the aspect runs, there is no tree to
derive a footprint from, so `found` is 0 for **every plan that reaches a normal
finalize**, and the failure is reported in the same field, same format, same severity as a
genuine coverage miss.

This is the epic's own theme reproduced inside the epic's own audit tool: *could not look*
and *looked and found nothing* share one representation, and the one that renders is the
alarming one.

## Solution

Two candidate fixes, not mutually exclusive:

- **Order the retrospective before `branch-cleanup`**, or before whichever step removes the
  worktree. This is the cheap fix but it collides with the retrospective wanting the merge
  outcome.
- **Give the aspect a non-worktree footprint source.** The merged/squashed commit is
  knowable at retrospective time (`branch-cleanup` records it — here `7201f8d2d`), and a
  `git show --name-only {merge_sha}` derivation needs no worktree. Prefer this: it also
  makes the check work in archived mode.

Whichever lands, the aspect **must not report `recall_pct: 0.0` when its footprint source
was unavailable.** An unavailable source is a distinct outcome from an empty result and
needs its own status (`skipped` + reason token), exactly as the chat-history aspect already
does with `transcript_unavailable` vs `transcript_too_large`.

## Impact

Affects every plan-retrospective run in finalize-step mode, i.e. every orchestrated plan.
The declared-vs-achieved coverage comparison — the deterministic half of the thoroughness
dial — has been structurally vacuous for all of them, while reporting a red check that
readers have presumably been discounting by hand. Note the second-order cost: a check that
is *always* red teaches its readers to ignore it, so the day it reports a real miss nobody
will look.

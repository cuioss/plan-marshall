envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:56:20Z

component=plan-marshall:phase-6-finalize
category=bug
proposed_title=Close the pre-merge comment barrier's check-then-act window before the merge call

# Close the pre-merge comment barrier's check-then-act window before the merge call

## Status

**Observed during `lane-router-reads-the-wrong-body`, NOT fixed.** Two review findings are **live on merged main** (`83a0466d2`) as a direct result. This is the highest-severity item from this plan's retrospective and it is *not* covered by the nine candidate-lessons `lessons-capture` filed — that step ran at 09:57Z, 45 minutes before the incident.

## What happened

Exact sequence from `logs/work.log` and `logs/decision.log`:

| Time (UTC) | Event |
|---|---|
| 09:42:59 | `automatic-review`: coderabbit (required) rate-limited, did not review. Operator authorised **merge-anyway** on pr-agent's review alone. |
| 09:59:24 | Merge-mutex `lock-waiting` — plan enters the FIFO admission queue. |
| 10:25:40 | `lock-owned` — admitted. |
| 10:27:04 | Pre-merge rebase advances HEAD `146fc9e7` → `07778c3b`. Trigger-A re-review deliberately not awaited (consistent with the 09:42 merge-anyway decision). |
| **10:27:25** | **Pre-merge comment barrier re-fetches and reads CLEAN** — "zero pending pr-comment findings, proceeding to merge". |
| **10:32:41** | **CodeRabbit's rate window reopens. It reviews the rebased HEAD `07778c3b` and posts 2 actionable findings (1 Major).** |
| ~10:42 | Platform merge queue merges PR #1049. |
| 10:42:06 | Operator chooses **dequeue-and-fix**. Too late — already merged. |

## The defect

The barrier is a **single-sample read**. It samples the comment state once, then hands off to a merge path whose completion is owned by the platform merge queue and takes an unbounded amount of wall time. Between the sample and the merge there is a wide, unguarded window — here **~15 minutes** — in which a review can land and be invisible to the gate that exists specifically to see it.

`pre_merge_comment_barrier=fail_into_loopback` was configured and *did its job correctly on the data it had*. The gate is not broken; its **sampling contract** is. This is textbook check-then-act (TOCTOU) at a human-timescale boundary.

## Why this is the epic's archetype

`branch-cleanup` reported `merged via queue, main pulled`. The barrier reported `clean`. Both are true statements about the moment each was evaluated, and together they read as "merged after a clean review check" — which is false. **A confident signal hiding a caveat: the caveat is that "clean" had an expiry the consumer never saw.**

## Proposed action

1. Make the barrier emit a **high-water mark** (latest comment id / timestamp per reviewer) rather than a boolean verdict, and persist it.
2. Re-query immediately before the merge call and **fail the merge when the mark advanced**. The merge call is the act; the check must be adjacent to it, not 15 minutes upstream.
3. Where a platform merge queue makes "immediately before" unachievable, the barrier verdict MUST carry its sample timestamp so a stale-clean is distinguishable from a fresh-clean by the consumer.
4. Consider a hard rule: **an unawaited-re-review decision (trigger-A skip) must widen the barrier, not narrow it.** In this run the operator's earlier merge-anyway was correctly propagated to skip the trigger-A await — but that propagation removed the last chance to observe the very review that then arrived.

## Owed follow-up (separate from this lesson)

Both CodeRabbit findings need a fix PR against main. They are described in messages filed alongside this one.

## Evidence

- `logs/decision.log` 10:42:06Z — `DEQUEUE MISSED - merge outran the operator decision`
- `logs/work.log` 10:27:25Z — `Pre-merge comment barrier: clean - zero pending pr-comment findings, proceeding to merge`
- `execution.toon` `branch-cleanup` step_params: `pre_merge_comment_barrier=fail_into_loopback`, `use_merge_queue=true`, `merge_queue_wait_budget_seconds=1800`
- aspect: `request_result_alignment` — `post_merge_regression[2]`

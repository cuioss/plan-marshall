envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:18:43Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=chat_history_analysis

# Merge-queue Monitor notifies per poll, not per state transition

## Context

The session transcript for this plan holds 920 raw turns. `extract-chat-signal` reduced them to 22 signal-classified turns. Of those 22:

- 2 are operator-authored (`/plan-marshall:plan-marshall plan=...` and one `continue`)
- 1 is a harness skill-reload notice
- **19 are byte-identical** Monitor notifications reading:

```
Monitor event: "PR #1076 merge-queue state"
event: pr-1076: OPEN CLEAN
```

86% of the plan's entire reduced chat signal is one repeated sentence reporting that nothing changed. The window is `branch-cleanup` (11:42:27Z Executing to 12:01:58Z Completed, ~19.5 min) with the merge lock held 11:43:17Z to 11:56:54Z.

## Root cause

The merge-queue waiter emits a notification on every poll rather than on a state transition. Its notification count therefore measures polling cadence, not events — and because every body is identical, no notification in the sequence is distinguishable from any other by content, including whichever one straddled the actual merge.

The secondary cost lands on the retrospective: any plan that waits on a merge queue will have its chat-history aspect dominated by waiter repetition, crowding out the operator turns that aspect exists to analyse.

## Proposed action

1. Notify on transition, not on poll: suppress a notification whose event payload is byte-identical to the previous one for the same monitored subject.
2. When a periodic heartbeat is genuinely wanted, make it say so and carry elapsed time (`still OPEN CLEAN after 8m`), so consecutive notifications differ and a reader can tell progress from repetition.
3. Independently, have `extract-chat-signal` collapse runs of identical notification bodies to one entry plus a repeat count before the reduction budget is applied, so the reduced transcript spends its budget on distinct signal.

## Evidence

- aspect: chat_history_analysis — `raw_turn_count: 920`, `reduced_turn_count: 22`, `distinct_harness_notification_bodies: 1` across 19 notification turns
- `logs/work.log` — `[STEP] Executing step: default:branch-cleanup` 11:42:27Z, `Completed` 12:01:58Z
- `logs/script-execution.log` — `manage-locks:merge_lock acquire` 11:43:17Z, `release` 11:56:55Z

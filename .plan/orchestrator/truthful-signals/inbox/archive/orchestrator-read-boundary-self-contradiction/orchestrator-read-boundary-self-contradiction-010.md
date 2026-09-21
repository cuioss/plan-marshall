envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:45:55Z

component=plan-marshall:manage-metrics
category=improvement
created=2026-07-28
bundle=plan-marshall

# A canonical-invocations block that documents 6 of the 11 values its argparse accepts

## What happened

`manage-metrics` SKILL.md documents `record-dispatch-boundary --termination-cause`
in two places — the `### record-dispatch-boundary` operations section and the
`## Canonical invocations` block — and **both** list the same six values:

```
{voluntary_checkpoint|task_complete_returned_verbatim|budget_yield|
 harness_cancellation|error|clean_exit_queue_empty}
```

The live argparse accepts **eleven**:

```
voluntary_checkpoint, task_complete_returned_verbatim, budget_yield,
harness_cancellation, error, clean_exit_queue_empty,
step_complete, blocked_user_review, blocked_session_restart,
task_batch_complete, agent_returned
```

Five undocumented values. This is not theoretical drift: **`step_complete` was used
seven times in this very plan** — it is the termination cause on every one of the
seven `6-finalize` dispatch-boundary rows.

The SKILL.md prose actively reinforces the wrong contract: *"Required — missing or
unrecognised values are rejected as script errors (there is no implicit fallback)."*
A reader takes that as an exhaustive enum. An agent following the documented contract
and encountering `step_complete` in a live artifact would classify it as an **invented
subcommand value** under the project's own "Never invent script subcommands" rule —
and would be wrong.

## Solution

**Rule:** when a closed enum in an argparse `choices` grows, the `## Canonical
invocations` block grows in the same change. That block is not commentary — the
plugin-doctor `manage-invocation-invalid` analyzer reads it as *source of truth* for
notation occurrences across the marketplace, so an incomplete block is an incorrect
oracle, not merely stale docs.

1. Add the five missing values to both the operations section and the canonical
   block, with a one-line meaning for each (the existing entries model this well —
   `clean_exit_queue_empty` carries its `loop-exit-guard` precondition inline).
2. Consider a structural guard: for `manage-*` scripts, compare each documented
   `{a|b|c}` enum in the canonical block against the live argparse `choices` and fail
   `quality-gate` on divergence. The comparison is mechanical and the data is already
   introspectable — this is the same class of deterministic check the
   `ARGUMENT_NAMING_*` cluster already performs for flag names.

## Impact

Adjacent to the epic theme rather than central, but it is the same failure shape at
the documentation layer: a block that *presents itself as authoritative and complete*
while silently covering half its subject. The index-completeness rule already recorded
in `agent-behavior-rules.md` — *"a newly-authored index/summary table must enumerate
every member of the set it indexes"* — states the obligation; this is a live violation
of it in a canonical block, which is the highest-stakes place for it to occur.

Cheap to fix, and the structural guard would retire the whole class.

Filed alongside a report-only observation from the same run: **seven argparse
rejections across six distinct components** (`manage-status phase-handshake`,
`manage-findings --resolution-detail`, `manage-execution-manifest compose`,
`git-workflow commit`, `ci --plan-id`, `manage-files --subdir`, `git-workflow
switch-and-pull` missing `--base`). No single component is the culprit, so that is
not filed separately — but the density is notable, and an incomplete canonical block
is one of the mechanisms that produces it.

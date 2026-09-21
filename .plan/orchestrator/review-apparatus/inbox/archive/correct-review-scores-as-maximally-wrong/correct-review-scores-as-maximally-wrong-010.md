envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T14:07:37Z

component=plan-marshall:manage-metrics
category=bug
bundle=plan-marshall

# SKILL.md lists 6 of 11 termination causes, and the missing loop-back value makes a passing gate read as an error

## Divergence 1 — the documented enum is incomplete

`manage-metrics/SKILL.md` documents the `record-dispatch-boundary --termination-cause` enum as **six**
values, in both the parameter table and the `## Canonical invocations` block:

```
voluntary_checkpoint | task_complete_returned_verbatim | budget_yield |
harness_cancellation | error | clean_exit_queue_empty
```

The shipped `argparse` surface accepts **eleven**:

```
voluntary_checkpoint, task_complete_returned_verbatim, budget_yield,
harness_cancellation, error, clean_exit_queue_empty,
step_complete, blocked_user_review, blocked_session_restart,
task_batch_complete, agent_returned
```

Five values are undocumented: `step_complete`, `blocked_user_review`, `blocked_session_restart`,
`task_batch_complete`, `agent_returned`.

This is not academic. **This plan used two of the undocumented values, nine times**: `step_complete`
(×8, all of 6-finalize) and `task_batch_complete` (×1, 4-plan). A caller reading SKILL.md would believe
every one of those nine calls was invalid — and SKILL.md explicitly states that unrecognised values
"are rejected as script errors (there is no implicit fallback)", which makes the omission read as a
prohibition rather than as a gap.

## Divergence 2 — there is no loop-back cause, so a passing gate is recorded as an error

The enum has no value for "the step completed successfully and returned a loop-back". So the three
`pre-submission-self-review` passes — **each of which found a genuine defect, which is the gate working
exactly as designed** — were recorded as:

```
08:03:03  error  231203
08:54:40  error  214202
09:25:55  error  250852
```

Three of the eleven 6-finalize dispatch boundaries are stamped `error` for successful defect-finding
work. Any downstream consumer computing an error rate over this file reads **27% error** on a run whose
finalize had zero step failures.

`blocked_user_review` exists and would have been closer, but neither it nor `error` says "found a
defect, looping back" — which is a *success* outcome for a review gate.

## Root cause

The enum grew in the script without the doc following, and it was designed around terminal outcomes
before loop-back became a first-class finalize control flow. `error` then absorbed everything that was
neither a clean exit nor a checkpoint.

## Proposed action

1. **Reconcile SKILL.md to the argparse surface** — all 11 values, in both the parameter table and the
   `## Canonical invocations` block. The `_analyze_manage_invocation.py` plugin-doctor analyzer reads
   that block as source-of-truth, so the divergence is machine-checkable and should become a lint rule:
   assert the documented enum equals the argparse `choices` tuple.
2. **Add a `loop_back` cause** and have the self-review / triage loop-back path emit it, so a
   defect-finding pass is no longer indistinguishable from a crash.
3. **Backfill nothing** — the existing rows stay; the taxonomy fix is forward-only.

## Cross-component pattern note

This is the **same archetype** as candidate-lesson `cl-005` from this plan's lessons-capture
("UNFIXED: automatic-review/SKILL.md documents a CLI surface the script no longer has"). Two
independent components, same defect shape, found in one run. That promotes it from an instance to a
**pattern**: the doc-vs-argparse contract is not mechanically enforced anywhere, so it drifts silently
in whichever component changes next. The lint rule in action (1) is the pattern-level fix; the
per-component doc edits are the instance-level fixes.

## Evidence

- `record-dispatch-boundary --help` — 11 `choices` values
- `manage-metrics/SKILL.md` — 6 values, parameter table and Canonical invocations block
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 8× `step_complete`, 3× `error`
- `work/metrics-dispatch-boundaries-4-plan.toon` — 1× `task_batch_complete`
- `status.metadata.phase_steps` — `pre-submission-self-review` outcome `done`,
  "3 passes, 3 findings all fixed at 97bd3e7 d40b9c4 8baf6a1 — 4th pass waived by operator"
- sibling instance: candidate-lesson `cl-005` (automatic-review), same run

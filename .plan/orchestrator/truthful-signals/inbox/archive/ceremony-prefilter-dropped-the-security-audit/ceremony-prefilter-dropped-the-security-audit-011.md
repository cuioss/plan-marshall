envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:54:10Z

component=plan-marshall:manage-metrics
category=bug
created=2026-07-29

# record-dispatch-boundary accepts 11 termination causes, documents 6, and the detector counts 2

The live argparse surface of `manage-metrics record-dispatch-boundary --termination-cause` accepts
**eleven** values:

```
voluntary_checkpoint, task_complete_returned_verbatim, budget_yield, harness_cancellation,
error, clean_exit_queue_empty, step_complete, blocked_user_review, blocked_session_restart,
task_batch_complete, agent_returned
```

`manage-metrics/SKILL.md` documents **six** — twice, in the Operations section and again in the
Canonical-invocations block — and describes the enum as closed ("missing or unrecognised values are
rejected as script errors; there is no implicit fallback"). `plan-retrospective`'s
`references/logging-gap-analysis.md` calls those same six "the canonical value set" and builds its
`DISPATCH_TERMINATION_CAUSE` rule on them.

This plan recorded **eight rows, none of which is in the documented six**: `step_complete` ×7 (all
of 6-finalize) and `task_batch_complete` ×1 (4-plan). The consequences compound:

- `analyze-logs` reports `unknown_count: 0` — which reads as *"the vocabulary is clean"* when what
  it actually means is *"no row used the one legacy value I know how to be suspicious of"*.
- The `> 50% agent-initiated re-dispatch` warning counts only `voluntary_checkpoint` +
  `task_complete_returned_verbatim`. With every row carrying `step_complete`, the denominator is
  eight and the numerator is zero. The rule is structurally incapable of firing.
- The `info` distribution finding enumerates the six documented causes, so a reader sees six zeroes
  and no mention of the eight rows that actually exist.

Five live causes have no documentation and no detector coverage at all.

## Solution

- **Reconcile the three surfaces in one change**: the argparse `choices`, the two enum listings in
  `manage-metrics/SKILL.md`, and the canonical set in `logging-gap-analysis.md`.
- **Make the detector population-derived, not literal.** `analyze-logs` should read the accepted
  vocabulary from the recorder rather than hardcoding six names, and should flag any row whose cause
  is outside the vocabulary it knows — replacing the `unknown`-only check, which is a
  single-legacy-value guard masquerading as a vocabulary check.
- **Add a plugin-doctor rule** asserting that an enum list inside a `## Canonical invocations` block
  matches the script's argparse `choices` exactly. This is the third documented instance of an enum
  widening in code without its documentation following.

## Impact

Every plan since the enum was widened has been recording causes the retrospective cannot see, and
the `unknown_count: 0` signal has been reporting that state as clean. The
agent-initiated-re-dispatch detector that lesson `2026-05-08-14-001` exists to power has been
silently inert for those plans.

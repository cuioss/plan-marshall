envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T11:40:20Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source=lessons-capture-self-observation

# The lessons-capture Signal Gate forwards COUNTS that no consumer can act on or reconcile

## Observation

Observed from inside the `lessons-capture` dispatch of this plan's own finalize run — the step is a direct
instance of the defect class this epic tracks, and of the class the plan itself just fixed one layer down.

The dispatcher's Signal Gate (`phase-6-finalize/SKILL.md` Step 3 item 4b) forwards three integers to the
`lessons-capture` body and explicitly forbids the body from re-deriving them, on the stated grounds that
"the dispatcher already paid that cost". Two of the three are, as forwarded, unusable.

### Defect A — `signal_script_failure_clusters_count` names no notation

The forwarded value was `1`: one distinct script notation failed during this plan. **Which one is not
forwarded**, and the body is barred from `manage-logging read --type work`, which is the only place the
`[FAILED]` / `[ERROR] ... script_failure` markers live.

The gate therefore tells the lesson author *"a script failed, and it is lesson-bearing"* while withholding
the only fact that makes it recordable. The count is sufficient to FIRE the gate and insufficient to ACT on
it. This finalize run consequently emitted no candidate lesson for its one script-failure cluster — the
signal fired, the envelope was spawned, and nothing was captured. That is a genuine, silent capture loss,
not a theoretical one.

Fix: forward the failing notations (a `signal_script_failure_notations[]` list) alongside the count. The
dispatcher already enumerated them to dedup by distinct notation — the information exists at the gate and
is discarded on the way out.

### Defect B — `signal_qgate_pending_count` is an undisclosed snapshot

The forwarded value was `3`. At capture time a per-phase sweep
(`qgate list --resolution pending` over `2-refine` / `3-outline` / `4-plan` / `5-execute` / `6-finalize`)
returned `filtered_count: 0` on **every** phase: every finding had been resolved by the time the body ran.

The count is not wrong — it is a snapshot taken earlier in the dispatch loop. But nothing in the forwarded
payload says so, and the body is told not to re-derive it. A reader of the step record sees "3 pending
Q-Gate findings" as a live figure. The number and the store disagree, with no discriminator distinguishing
"3 are pending now" from "3 were pending when the gate ran, all since resolved".

Fix: either re-evaluate at dispatch time, or label the field as a snapshot with the observation point
(`signal_qgate_pending_count_as_of`). Same *which zero is this* discipline `inbox list`'s `inbox_state`
already applies — a count whose meaning depends on when it was taken must carry when it was taken.

## Rule

When a gate forwards a derived count to a downstream consumer AND forbids that consumer from re-deriving it:

1. **Forward the identifying detail, not just the cardinality.** A count that fires an action must carry
   enough to perform the action. "N of something failed" with no identity is a signal that can only be
   acknowledged, never discharged.
2. **A forwarded count is a snapshot; say so.** Either re-derive at the point of use or stamp the
   observation point. A no-recompute instruction converts every staleness window into an
   undetectable disagreement, because the one party positioned to notice has been told not to look.
3. **The forbid-recompute optimisation is only sound when the payload is self-sufficient.** Cost-saving that
   strips the consumer's ability to do its job is not an optimisation; it is a silent capability removal that
   still reports success.

## Cross-reference

This is the same shape as the defect the plan just fixed: `display_detail` carried a confident prose summary
while the underlying facts were unrecorded, so no consumer could answer a structured question. Here the
Signal Gate carries a confident integer while the underlying identity is unrecorded, so no consumer can act.
The plan retired the pattern one layer down and reproduced it one layer up, in the very step that captures
its lessons.

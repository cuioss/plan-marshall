envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:51:10Z

# A bare effort resolve leaves its dispatch unattributable, not just unlogged

component: plan-marshall:manage-config
category: anti-pattern
confidence: medium
source_plan: plan-truth-157
source_aspects: execution_context_dispatch_audit

## Context

The dispatch audit's `shape_violation` block evaluated a population of 32 and found 1 violation: one
`effort resolve-target` record in `decision.log` carrying `role=None` has no matching `[DISPATCH]` emission
in `work.log` (`resolved=1, dispatched=0`). Every other role is clean — `phase-2-refine` 1/1,
`phase-3-outline` 3/3, `phase-4-plan` 2/2, `phase-5-execute` 4/4, `phase-6-finalize` 16/16,
`post-run-review` 2/2, `verification-feedback` 3/3, each with `delta: 0`.

The resolve seam emits the `[DISPATCH]` work-log line and its paired decision-log record only when
`--workflow` is supplied; a bare-level query carries no dispatch context and so emits no work-log line. The
always-loaded rules already say this: "a resolve that omits `--workflow` is a bare-level query and leaves the
dispatch with no audit trail."

The part worth recording is the second-order consequence. The offending row's `foreign_caller_lines` is 0, so
the audit can count the omission but cannot name the call site that made it. The one dispatch in this plan
with no audit trail is also the one the audit cannot attribute — so the finding is countable and not
actionable.

## Root cause

Caller identity rides on the same optional flag as the work-log emission. Omitting `--workflow` suppresses
both the `[DISPATCH]` line and any record of who resolved, so the two failure modes cannot be separated
after the fact: an omission that was legitimate (a genuine bare-level query, which needs no trail) looks
identical to one that was a missing `--workflow` on a real dispatch.

## Proposed action

Have the resolve seam record the caller identity on the decision-log side even when `--workflow` is absent. A
bare resolve then remains correctly unaccompanied by a `[DISPATCH]` line — that part is by design — while
`shape_violation` gains the ability to name the call site it is reporting. The finding becomes actionable
without changing what counts as a violation.

## Evidence

- aspect: execution_context_dispatch_audit — `shape_violation` reports `status: evaluated`,
  `evaluated_population: 32`, `violations: 1`, with the finding text "1 resolve record(s) for role=None in
  decision.log have no matching [DISPATCH] emission in work.log (resolved=1, dispatched=0)"
- aspect: execution_context_dispatch_audit — `by_role` row `"",1,0,1,0`: one resolve, zero dispatch lines,
  delta 1, and zero foreign caller lines
- `agent-behavior-rules.md` § Principle 2 states the emission contract and the bare-query consequence, which
  is why the omission itself is expected behaviour and the *unattributability* is the finding

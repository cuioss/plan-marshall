envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=finding
created=2026-08-09T20:36:16Z

# get-module-context can never succeed at phase-3 for a `use_worktree=true` plan

Routed here on the finding's own explicit instruction: `1d3916` was filed during this plan's
outline with the note "latent defect in a component this plan does not target — route to the
truthful-signals epic inbox at finalize as a separate finding, do not fold into this plan."

## Observation

`manage-solution-outline get-module-context` resolves the worktree face **eagerly** and exits
non-zero while `worktree_state=pending`.

Under ADR-002 deferred materialization, the worktree is not materialized until
`phase-5-execute` Step 2.5. So for any plan with `use_worktree=true`, `worktree_state` is
necessarily `pending` throughout phase-3-outline, and the verb **can never succeed at the phase
that calls it**. This is a structural impossibility, not a race or an environment-specific failure.

## Observed consequence in this plan

The outline's **Architecture Hints section was omitted** rather than rendered empty. The reader of
`solution_outline.md` cannot tell that a section was dropped because a verb structurally could not
run — the absence looks like "no hints applied".

That is the epic's subject in miniature: the failure is silent at the artifact, and the artifact is
what every later phase reads.

## Why it is worth staging

Two distinct problems, and the second is the durable one:

1. **The eager resolution** — `get-module-context` should tolerate `worktree_state: pending` and
   resolve against the plan's pre-materialization face, since that is the only state it will ever be
   called in from phase-3.
2. **The silent omission** — whatever the fix to (1), a section that could not be built should be
   rendered as an explicit "could not resolve" rather than dropped. A dropped section and an empty
   section are indistinguishable to the reader, and neither is distinguishable from "the tool ran
   and found nothing".

Fixing only (1) leaves the general omission behaviour in place for the next verb that fails.

## Scope note

`plan-marshall:manage-solution-outline` was outside this plan's declared surface
(`manage-providers`, `tools-file-ops`, `manage-findings`, `tools-integration-ci`,
`manage-architecture`, `opencode/emitter.py`), so it was deliberately not touched. Staging it is a
clean, self-contained job — one verb's precondition handling plus one renderer's absent-section
behaviour.

## Provenance

- finding `1d3916`, type improvement, severity warning, component `plan-marshall:manage-solution-outline`
- filed 2026-08-09T12:06:09Z during phase-3-outline of PLAN-TRUTH-070
- plan landed as PR #1132 / `ff4462148`; this finding is unresolved residue and does not survive the
  plan directory

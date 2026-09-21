envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:42:56Z

# Fail an executor regeneration that derives zero surfaces where the previous one had surfaces

component: plan-marshall:tools-script-executor
category: bug
confidence: high
source_plan: executor-rejects-invalid-invocations-before-spawn
source_pr: 1127

## Context

At the very end of finalize, the documented on-main executor regeneration ran through
`project:finalize-step-sync-plugin-cache` and reported `status: success`. It had in fact
produced a **surfaces-less executor**: the run emitted no `surfaces_derived` line at all.
Probed live, `manage-tasks nuke` fell through to argparse *after* spawn instead of being
rejected pre-spawn — so this plan's headline guard was NOT live on main despite a green
sync and a green regen. Recovery required running the merged-source generator directly
(`--marketplace --marketplace-root . --force`), which derived 106 surfaces over 148
scripts; the same probe was then correctly rejected pre-spawn with a corrective.

The same shape was hit independently by a fix agent during phase-5 execute, so this is a
recurrence within a single plan, not a one-off.

## Root cause

`generate_executor` treats "derived nothing" and "derived everything" as the same
outcome. The **only** observable distinguishing them is the *absence* of a surface-stats
line in the output, and nothing consumes absence. Running the generator through the
executor notation resolves it from the plugin cache, which is the path that produced the
empty derivation.

This is a fail-open at the last gate: it manufactures a green finalize over an inert
guard, and the failure is invisible to every downstream check because a missing line
looks identical to a quiet success.

## Proposed action

`generate_executor` already computes `surfaces_reused` and `surfaces_derived`, and
`read_previous_surfaces` already knows how many entries the outgoing executor carried.
Add a post-generation assertion: when the previous executor carried N > 0 surface entries
and the new generation emits 0 (neither derived nor reused), exit non-zero rather than
reporting success. Emit the surface-stats line unconditionally — including the zero — so
that consumers assert on a present value instead of inferring from an absent one.

## Evidence

- decision.log `[2026-08-09T14:26:39Z] [WARNING] [5f800e] (project:finalize-step-sync-plugin-cache)` — full first-party account of the false green and the manual recovery.
- status.json `phase_steps["6-finalize"]["project:finalize-step-sync-plugin-cache"]` — `outcome: done`, `display_detail: "10 bundles synced; on-main executor regenerated (106 surfaces)"`, recorded only after the hand recovery.
- decision.log `[2026-08-09T00:45:06Z] [b5604b]` — the healthy shape for comparison: 148 registered, 106 derived, 0 reused, 42 not derivable.

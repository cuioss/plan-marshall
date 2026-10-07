envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=candidate-lesson
created=2026-09-19T14:24:52Z

component=plan-marshall:phase-2-refine
category=improvement
created=2026-09-19
bundle=plan-marshall

# Preserve-then-move recovery for pre-plan main-checkout work

PLAN-01 (phase gates in manage-status) was first authored directly on main before the plan existed — a 2-refine violation. The work was preserved as `work/preserved-plan01.patch`, moved into the plan worktree, and verified there, so no implementation was lost and the phase gate it violated stayed meaningful.

## Solution

Repair rather than discard: capture the pre-plan diff as a patch artifact, relocate it into the worktree, and re-verify under the plan's own gates before merging.

## Impact

Plans that discover finished work on main mid-refine can adopt this recovery instead of forcing a rewrite or silently grandfathering unreviewed code.

## Evidence

- invariant_summary: main_dirty_files drift 1-init -> 2-refine (pre-plan PLAN-01 files plus uv.lock)
- plan phase-gates, PR #1540, epic process-compliance

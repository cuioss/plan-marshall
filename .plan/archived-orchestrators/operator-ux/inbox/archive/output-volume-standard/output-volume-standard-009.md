envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T16:08:42Z

component=plan-marshall:manage-tasks
category=bug

# pre-commit-verify-freshness returned two contradictory verdicts for one unchanged tree

## Observation

On plan `output-volume-standard` the `pre-commit-verify-freshness` gate was called twice over the same worktree with no intervening tree change, and took two different routes:

- **First call** — `status: stale`, `reason: build_scope_narrow`. It scanned the ledger, found `kind=build` rows matching worktree sha `85368a1d`, and refused because each canonical (`quality-gate` / `test-compile` / `module-tests`) covered too few analyses to be cited for this change.
- **Second call**, after running the covering canonical `verify` (green, 23951 tests) — `status: fresh`, `reason: "plan footprint touches no build_map glob — only non-buildable files changed"`, with the message "build-decision ruled a build not_necessary for this footprint, so no `kind=build` entry can exist and none is required. Gate permitted without a ledger scan."

The second verdict short-circuits on a build-decision verdict BEFORE the ledger scan the first call performed. Both cannot be right for one unchanged tree: either the first call should also have short-circuited and its scope-narrow refusal was spurious, or the second should have scanned and its no-build-needed verdict is wrong.

## Recommended rule

Order the gate's routes deterministically: the build-decision short-circuit is a property of the footprint, so it must be evaluated FIRST and identically on every call, before any ledger scan. A gate whose route depends on call ordering rather than on its inputs cannot be cited as evidence, because the caller cannot tell which question it answered.

## Blast radius on this run

Contained. The push proceeded on independent evidence — a whole-tree `verify` green at that exact tree — not on the `fresh` verdict alone. The defect sits outside this plan's three-file documentation footprint; fixing it would have converted a build-`not_necessary` PR into a script change requiring a full verify build.

## Evidence

- Plan: `output-volume-standard` (epic `operator-ux`)
- Q-Gate finding `a03f17`, phase `6-finalize`, type `improvement`, component `plan-marshall:manage-tasks`
- Resolution: `taken_into_account` — operator disposition at the wait-region triage gate, held for a follow-up plan that owns `manage-tasks`

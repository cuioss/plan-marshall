envelope_version=1
sender_type=plan
sender_id=opencode-bootstrap-executor-fix
epic=process-compliance
kind=finding
created=2026-09-29T06:44:34Z

# Finding: a local green `verify` was contaminated by untracked generated target trees

## What happened

During phase-6-finalize of `opencode-bootstrap-executor-fix`, the pre-push `verify`
reported 28,361 tests green on a SHA that CI then failed twice.

Cause: `./pw generate --target opencode` had been run earlier in the plan, leaving
a gitignored `target/` tree in the long-lived worktree.
`test/plan-marshall/plan-marshall/test_target_tree_foundational_skill_freshness.py`
asserts over generated target trees and refuses to read an empty population as
clean. Locally the population existed; on a clean CI checkout it did not.

The test was right. The local green was not evidence about the tree that was pushed.
`build-pyproject clean` does not remove generated target trees.

## Fix already landed on the plan branch

`.github/workflows/python-verify.yml` gained `pre-verify-goals: 'generate'` /
`pre-verify-args: '--target all --output target'`. That required a
cuioss-organization release (v0.34.0), because the keys resolve inside the
`read-project-config` action rather than the workflow file — pinning the reusable
workflow commit alone would have silently skipped them.

## What is still owed (process-compliance)

- A pre-push check that refuses a green verdict when the worktree carries
  untracked generated state under a path a tracked test scans (`target/`).
- Local verification must follow CI's order: generate `--target all --output target`
  first, then `verify`.

## Shape

The same plan produced both halves of one failure class: a guard over an EMPTY
population (the CI failure above) and a guard over the WRONG population
(CodeRabbit's flat-root coverage finding, where both sides of a coverage check read
nothing on the base the runtimes actually return). Checking that a guard has a
population is not the same as checking it has the right one.

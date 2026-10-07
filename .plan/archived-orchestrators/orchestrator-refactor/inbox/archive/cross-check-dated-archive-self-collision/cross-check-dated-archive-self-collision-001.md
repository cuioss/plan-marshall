envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:09Z

component=python-verify-ci
category=bug
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Run the test build for any change to .plan/marshal.json

## Context

During one plan run, main went red three times from commits that changed only the tracked `.plan/marshal.json`. Each one stalled the plan until a human repaired main:

- #1666 committed `orchestrator.use_worktree: true`; `test_committed_marshal_json_surfaces_every_orchestrator_knob` went red. Plan paused in 5-execute for 1h57m (fixed by #1668).
- #1669 committed `runtime.target=opencode`; 160 tests failed. Plan paused in finalize for 4h14m.
- #1677 committed `runtime.target=antigravity`; 248 tests failed in the plan's own merge-group run, the queue ejected PR #1676, the landing gate spent its full 1800s budget and a loop-back iteration was consumed. Plan paused 11h57m (fixed by #1679).

About 18 hours of stall on a plan whose own tests were green throughout.

## Root cause

OBSERVED: the test suite reads the committed `marshal.json` (key order, declared knobs, resolvable finalize steps), so that file is test input. `.github/workflows/python-verify.yml` sets `skip-on-docs-only: true`, described there as skipping the heavy build "when every changed path is non-building (docs/config)".

HYPOTHESIS (not verified from the plan's artifacts): the three PRs were classified config-only and landed without the test build. The same workflow comment says a merge_group run still verifies; had that held for #1677, its own queue entry should have failed. Which of the two is true was not checked.

Second cause, OBSERVED in two of three incidents: a machine-local value (`runtime.target`) was written into the tracked file by a steward-maintained-artifacts landing.

## Proposed action

1. Treat `.plan/marshal.json` as buildable in the footprint gate, or split the config-contract tests into a job that always runs.
2. Establish whether merge_group runs really bypass the skip, and correct the workflow comment or the gate.
3. Keep `runtime.target` out of the tracked file (it belongs in the git-ignored run configuration), and add a contract test that fails when it appears.

## Evidence

- decision.log 2026-10-01T07:54:25Z, 11:22:32Z, 20:21:35Z (three red-main records with failure counts and the offending PR)
- work.log 2026-10-01T20:16:22Z (queue-landing gate timeout), 2026-10-02T08:18:14Z (resume after #1679)
- chat history: three operator turns saying main is fixed, continue
- metrics: 5-execute idle 2h37m; finalize unclosed with two further stalls

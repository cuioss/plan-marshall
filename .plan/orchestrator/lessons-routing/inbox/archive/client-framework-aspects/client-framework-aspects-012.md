envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:55Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-15-plan-12-residual-fixes-006.md`, sender plan `plan-15-plan-12-residual-fixes`, created 2026-11-24T11:11:52Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: git-workflow commit and push refusals in 6-finalize when making an inline correction after the review bots

**Source plan:** plan-15-plan-12-residual-fixes
**Signal:** signal_script_failure_clusters_count=3. This message covers the `plan-marshall:workflow-integration-git:git-workflow` notation.
**Suggested category:** anti-pattern (inline-correction commit path)
**Suggested component:** plan-marshall:workflow-integration-git (commit guard) and plan-marshall:phase-6-finalize (wait-region inline-correction route)

## Records

### 1. Source-tree commit refused, `reason: no_sanction` (work log 09:49:17Z, exit 1)

While fixing the 10 bot findings in the wait-region triage, the caller tried to commit the 8 changed doc paths from 6-finalize without any sanction the guard accepts. The guard refused with this text: "no step id from the composed phase-6 manifest, no open loop-back fix task and no review-rubric section-6 inline-correction record". The run recovered: the commit landed as inline commit 74e1f9b3, and loop-back iteration 1/5 for wait-region-unified-triage re-entered the finalize steps.

**Rule:** a source-tree commit in 6-finalize needs one of these three, in place before the commit call:
- `--step` with a composed phase-6 manifest step id;
- an open loop-back fix task;
- a recorded section-6 inline-correction record.

Record the sanction first, then commit. Do not commit first and read the refusal to learn the contract.

### 2. `commit --push` without a message (operator-reported; not found as a separate marker line in the work log)

A `commit --push` was issued without a commit message, and the verb requires one.

**Rule:** always pass the message to `commit`, including when `--push` is combined with it.

### 3. Push refused with `head_not_validated_by_gate` after a post-gate commit (operator-reported, expected behaviour)

A commit made after the pre-push quality gate moved HEAD past the validated SHA, so the push was refused. This is the intended guard. It is recorded here only so the orchestrator does not classify it as a defect. The recovery was to re-fire pre-push-quality-gate on the new head (10:04:07Z), then push (10:23:59Z).

**Rule (knowledge):** any commit after the pre-push gate requires a gate re-fire before push. Sequence the inline corrections before the gate, not between the gate and the push.

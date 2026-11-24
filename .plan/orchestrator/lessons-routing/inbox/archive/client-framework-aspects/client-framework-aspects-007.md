envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:53Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-12-documentation-review-consolidation-008.md`, sender plan `plan-12-documentation-review-consolidation`, created 2026-11-23T20:29:08Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: a finalize review-fix commit was refused for lack of a sanction

Source signal: script-failure cluster `plan-marshall:workflow-integration-git:git-workflow`
(work log 2026-11-23T19:06:09Z, entry a01eef).

## Observation

The first automatic-review round left review-bot fixes to make (4 changed paths under `benchmarking/...`). A
source-tree commit was then attempted directly in 6-finalize, and git-workflow refused it:

```
script_failure ... exit_code=1 failure_kind=script_internal_failure
"Source-tree commit refused in 6-finalize: no step id from the composed phase-6 manifest, no open loop-back fix
task and no review-rubric section-6 inline-correction record." reason: no_sanction, step: null
```

The run then went down the sanctioned path: a functional-review/code-review re-dispatch, a second
pre-push-quality-gate and push. So the guard worked. The cost was one failed call and the review-fix commit going
through a detour.

## Candidate rule

When verification-feedback or automatic-review fixes have to land in 6-finalize, pass `--step {composed phase-6
step id}` on the commit, or open a loop-back fix task first. Never issue a bare commit. The verification-feedback
workflow should state the sanction it needs before it calls the commit.

Component hint: plan-marshall:plan-marshall (workflow/verification-feedback.md) / plan-marshall:workflow-integration-git.

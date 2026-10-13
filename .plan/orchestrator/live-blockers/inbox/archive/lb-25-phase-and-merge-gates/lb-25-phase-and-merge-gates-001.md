envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:06Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Accept ci-verify producers in verification-feedback or map them explicitly

## Context

During 6-finalize of lb-25-phase-and-merge-gates, ci-verify went red and the dispatcher handed the failure to `verification-feedback` with `producer: ci-verify-build`, as `phase-6-finalize/standards/ci-verify.md` documents (one verification-feedback dispatch per producer string such as `ci-verify-build`, `ci-verify-policy`). The leaf returned `status: error, error: unknown_producer` and triaged nothing; the orchestrator had to route the CI failure itself.

## Root cause

Contract gap between two documents: Step 1 of `plan-marshall/workflow/verification-feedback.md` accepts only `build-runner`, `sonar`, `pr-comment`, `plugin-doctor`, `pr-state`, `finalize-feedback`, while `ci-verify.md` dispatches `ci-verify-*` producers. No accepted producer covers the `type: triage` / `[ci_build_failure]` findings ci-verify files.

## Proposed action

Either add the `ci-verify-*` producer family to the verification-feedback accept-set with its finding-type mapping, or change `ci-verify.md` to dispatch an already-accepted producer with an explicit `finding_type`. Add a contract test that every producer string a dispatcher names is in the workflow's accept-set.

## Evidence

- aspect: chat_history_analysis - verification-feedback leaf: "Step 1 of verification-feedback.md only accepts build-runner, sonar, pr-comment, plugin-doctor, pr-state and finalize-feedback ... ci-verify.md says the dispatcher runs one verification-feedback per producer string (ci-verify-build, ci-verify-policy, ...)"
- 4 pending findings 2fd0f1, 0b3c8b, 6d5caa, ffe5a8 (all `type: triage`) were left for the orchestrator

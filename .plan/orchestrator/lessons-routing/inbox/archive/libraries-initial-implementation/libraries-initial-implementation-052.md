envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:33Z

component=plan-marshall:phase-6-finalize
category=bug
title=phase-6-finalize merge gate: an optional review bot that refused on size is treated as an unproven required reviewer, and only the gate's own option label resolves it
source_lesson=2026-11-22-21-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# phase-6-finalize merge gate: an optional review bot that refused on size is treated as an unproven required reviewer, and only the gate's own option label resolves it

- Source signal: finalize merge gate of plan-12-forms-kinds-schema-layout (PR 54), gate result `merge_participation_unproven`.

## What happened

The pull request had two review bots. CodeRabbit is required. Sourcery is optional, and it refused the PR because of its size (a size refusal, so it never reviewed). The merge gate counted Sourcery as a required reviewer that had not participated and returned `merge_participation_unproven`, which blocks the merge.

The only way through was an operator override. The gate accepts the override only as its own option label. Free-text approval was refused, so the first attempts to explain "sourcery is optional" had no effect.

## Why it matters

A size refusal from an optional bot is a known, permanent state of a large PR, not missing proof. Treating it as an unproven required reviewer turns every large PR into an operator interruption, and the free-text refusal makes the cause hard to see.

## Candidate rule

- The participation check should read the bot's configured requirement. An optional bot that refused (size, quota, unsupported language) is recorded as `not_applicable`, not as `unproven`.
- When the gate does need an override, its refusal message should print the exact option label it accepts.
- Until the gate is fixed: when an optional bot refused, ask the operator with the gate's option label at once instead of trying free text.


## Recurrence in the next plan (plan-23-forms-hardening, inbox plan-23-forms-hardening-007)

- Source signal: wait-region / branch-cleanup merge gate (decision log 11:38:05 and 12:00:50; PR #59). `pre_merge_gate merge --route merge-queue` refused with `merge_participation_unproven` (`authorizable=true`, `unproven_bots=sourcery`): coderabbit participated, sourcery was `refused_structural` (the 150,000-diff-character cap, 2,913 changed lines), and sourcery is in `optional_bots`, while the barrier-side `review_completeness` check had reported `participation_complete=true`. The two gates disagree on the same PR and head (`43dad67`); the merge was blocked until the operator selected "Accept the coverage gap (record reason)".
- The grant verb accepts only the gate's own override labels, so an operator answer to a question phrased differently could not be turned into a ruling and the question had to be asked again in the gate's own terms (orchestrator-reported). Second plan in a row (PLAN-12 was the first): one predicate should decide both gates, and until it does the operator prompt at this refusal is phrased with the gate's own labels.

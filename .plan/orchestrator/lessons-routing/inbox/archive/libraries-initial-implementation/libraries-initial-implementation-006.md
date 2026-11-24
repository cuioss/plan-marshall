envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:02Z

component=plan-marshall:phase-5-execute
category=improvement
title=phase-5-execute: a coverage build owed by a fix task has no slot in the return when the manifest lacks verify:coverage
source_lesson=2026-11-18-07-005
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# phase-5-execute: a coverage build owed by a fix task has no slot in the return when the manifest lacks verify:coverage

# Candidate lesson: a coverage build owed by a fix task has no slot in the execute return when the manifest lacks verify:coverage

- Source signal: plan-retrospective, chat-history aspect (TASK-9 and TASK-10 returns in 5-execute re-entries, 2026-11-17/18)
- Manifest: `phase_5.verification_steps` = [`verify:quality-gate`, `verify:module-tests`]; no `verify:coverage`

## What happened

TASK-9 added coverage tests so Sonar's new-code coverage would reach 0.80. Its coverage build resolved to the orchestrator tier, so the leaf handed it back with `pending_verify_steps: [verify:coverage]`, an id the manifest never composed. TASK-10 later finished with `verification_handback: false` and the coverage build still not run; it could only mention it in a free-text `coverage_handback_note`, because "the coverage build is not in this plan's list of phase-5 verification steps, so the return format cannot carry it". The orchestrator ran the coverage build from the TASK-9 hand-back, but on the TASK-10 pass the only trace was the note.

## Candidate rule

When a fix task's own verification needs a build that the manifest did not compose (here coverage, added because a Sonar coverage gate failed), either the loop-back that creates the task should add the step to `phase_5.verification_steps`, or the execute return should carry a structured "owed, uncomposed" build list next to `pending_verify_steps`. A free-text note is not a hand-back the orchestrator is obliged to act on.

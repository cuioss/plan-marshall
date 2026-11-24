envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:43Z

component=plan-marshall:phase-4-plan
category=improvement
title=phase-4-plan: a helper added in module A and consumer migrations in module B are planned as separate tasks per module from the start
source_lesson=2026-11-24-07-007
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# phase-4-plan: a helper added in module A and consumer migrations in module B are planned as separate tasks per module from the start

Source: Q-Gate finding afd2ca, phase 4-plan, module_mapping_validator, test/impl module mismatch for deliverable 5, resolution taken_into_account.

Observation: module_testing TASK-10 declared ten git-core test files while its sibling implementation TASK-9 declared only git-testing files. The git-core tests migrate absence assertions onto the new git-testing generator and fixture; they do not exercise the changed git-testing code. No doc/developer/test-impl-mapping.adoc exists to record such a pairing.

Resolution in run: the ten git-core tests were split into TASK-13 (module_testing, module git-core, depends on TASK-9); TASK-10 kept the six git-testing tests; manifest recomposed with envelope_count 4.

Candidate rule: when a deliverable adds a helper in module A and migrates consumers in module B, plan the consumer migration as its own module_testing task in module B from the start.

Context: plan plan-20-leftover-fixes-2, PR 69 (merged f7eda4e).


Source: inbox plan-20-leftover-fixes-2-006 (Q-Gate finding afd2ca). Related: 2026-11-20-07-002 (every affected file of a deliverable belongs to the module the deliverable declares).

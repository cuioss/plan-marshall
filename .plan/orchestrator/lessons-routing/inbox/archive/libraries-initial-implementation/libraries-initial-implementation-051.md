envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:32Z

component=plan-marshall:phase-3-outline
category=improvement
title=record component assessments in the deep lane so the coverage checks can run
source_lesson=2026-11-22-13-006
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# record component assessments in the deep lane so the coverage checks can run

# Candidate lesson: the deep-lane outline records no component assessments, so the coverage checks never run

- Source signal: plan-retrospective of plan-09-store-release-index-listeners (inbox plan-09-store-release-index-listeners-026; outline-vs-shipped aspect and the Q-Gate returns).

## What happened

The deep-lane outline recorded no component assessments. Both Q-Gate passes (outline and plan) reported `assessment-coverage` and `missing-coverage` as not run, so they wrote only partial hashes and no full-pass row, and the outline-vs-shipped aspect found all 37 shipped paths unassessed, including the 7 added by fix tasks. The outline still listed the 30 files correctly, but nothing assessed them.

## Candidate rule

The deep-lane outline writes one assessment per declared file (include or exclude, with a certainty), or Q-Gate reports an empty assessment store in the deep lane as a finding instead of a silent "not run". Owning component: `plan-marshall:phase-3-outline`.


## Recurrence in a later plan (plan-23-forms-hardening, inbox plan-23-forms-hardening-010)

- Source signal: plan-retrospective (outline-vs-shipped aspect and the Q-Gate hand-backs). The deep outline lane (10 deliverables, 32 mutation paths) left the per-file assessment store empty (0 records); both Q-Gate runs (3-outline and 4-plan) reported `assessment-coverage` and `missing-coverage` under `not_run_validators` and wrote `deliverable-hashes --write --partial`, so no whole-outline aggregate row exists; 29 of 29 shipped paths are `touched_but_unassessed`. Second plan in a row on the deep lane. Same rule: write one assessment per declared file before the Q-Gate, and report an empty store on a deep-lane plan as a finding.

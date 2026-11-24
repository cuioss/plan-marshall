envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:20Z

component=plan-marshall:phase-4-plan
category=bug
title=phase-4-plan: sync Affected files when a Q-Gate under-coverage finding is taken into account
source_lesson=2026-11-19-14-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# phase-4-plan: sync Affected files when a Q-Gate under-coverage finding is taken into account

# Candidate lesson: resolving a Q-Gate under-coverage finding as `taken_into_account` leaves the deliverable's Affected files unchanged

- Source signal: plan git-core-incore-write-cas (inbox git-core-incore-write-cas-015 and -004), plan-retrospective (manifest-decisions, artifact-consistency, request-result-alignment), component `plan-marshall:phase-4-plan`, confidence high.
- Evidence: manifest rule M6 reports `declared_vs_realized_set` fail with the culprits `README.adoc` and `RecordingTransportProtocol.java`; both trace to Q-Gate findings 04f7cd and acb2bd.

## What happened

The 4-plan Q-Gate raised two `scope_criterion_validator` under-coverage findings: 04f7cd (the root `README.adoc` states the `git-core` state but is not in deliverable 4's affected files) and acb2bd (`RecordingTransportProtocol.java` must change to observe the transport timeout but is in neither deliverable 5's affected files nor task 8's steps; it records only the URL and the credentials provider and exposes no timeout accessor). Both were resolved `taken_into_account`. Both files were then modified, yet neither was ever added to the deliverables' declared files, so the finding was closed while the declaration gap it was raised for stayed open.

## Root cause

Resolving an under-coverage finding as `taken_into_account` only adjusts the task description. Nothing requires the remedy the finding itself names ("add the file to the deliverable and the task, or document the exclusion") to reach the outline's Affected files and `references.json`.

## Candidate rule

When a Q-Gate finding of the under-coverage class is resolved `taken_into_account` (or `fixed`), require the resolver either to add the named path to the deliverable's Affected files (and re-run `sync-affected-files`) or to record an explicit exclusion, and reject the resolution otherwise. The 3-outline counterparts follow the same rule. The planning-side half of the same finding (acb2bd): when a task's test observes a property through an existing test helper, check at plan time that the helper exposes that property, and list the helper as a modified file in the deliverable when it does not.

envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=truthful-signals
kind=candidate-lesson
created=2026-09-24T08:06:29Z

envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=truthful-signals
kind=candidate-lesson
created=2026-09-24T08:11:00Z

component=plan-marshall:phase-3-outline
category=improvement
title=Reconcile references-only files into the outline declared surface
confidence=medium
source_plan=truth-147-lane-reports-green
source_aspects=artifact-consistency,request-result-alignment

# Reconcile references-only files into the outline declared surface

## Context

On plan truth-147-lane-reports-green, artifact-consistency found 11 files
present in references but outside every deliverable's declared modification
surface (e.g. manage-status assert-step-recorded sources and their tests),
with overall recall at 100% on the 15 declared files. The manifest aspect
absorbs the difference, so the drift ships silently.

## Root cause

The outline verification checks declared-vs-realized recall but has no
references-subset-declared direction: files the plan touches that no
deliverable declares are forwarded, never flagged at the declaring phase.

## Proposed action

Add an outline-phase check that every references entry is covered by at least
one deliverable's declared file surface (Affected files plus the
survey-scope pair), or carry an explicit survey-scope annotation — so the
declaring phase owns the full mutation surface instead of the manifest
aspect absorbing it downstream.

## Evidence

- aspect: artifact-consistency — affected_files_exact_match info, references_only 11, forwarded_to_manifest true
- aspect: request-result-alignment — scope creep 11 files outside declared surface

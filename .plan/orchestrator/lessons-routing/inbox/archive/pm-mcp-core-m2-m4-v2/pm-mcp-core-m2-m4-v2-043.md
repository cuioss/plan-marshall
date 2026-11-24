envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T17:37:49Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-11-20
bundle=plan-marshall
title=Resolve the realized footprint across every PR of a multi-PR plan

# Resolve the realized footprint across every PR of a multi-PR plan

## Context

PLAN-V2-158 shipped in two pull requests: #525 (deliverable 1, merged c9d9c5a4, about 73 files) and #529 (deliverables 2 to 6, merged 4917a034, 81 files). The retrospective's shared footprint resolver answered from the `realized_capture` tier with PR B's 81 files only. `check-artifact-consistency` therefore failed `affected_files_recall` at 48% (74 of 154 declared) and `check-manifest-consistency` rule M6 reported 80 declared-but-unrealized paths, every one of them a PR A file that did ship.

## Root cause

The realized capture (and the merge-commit / PR-landing tiers) are keyed to one branch head / one PR, so a plan whose work landed through more than one PR reports its earlier PRs as unrealized.

## Proposed action

When a plan records more than one PR (e.g. `status.metadata.pull_request_cut`, or several create-pr / merge facts), union the footprints of all of its merged PRs, or mark the comparison `inconclusive` with a multi-PR caveat instead of failing recall.

## Evidence

- aspect: artifact_consistency — affected_files_recall fail, recall 48%, missing list = PR A files (ADR 029, ProfileStages, WorkerParameters, ...)
- aspect: manifest-decisions — declared_vs_realized_set fail, outline_only 80, footprint tier realized_capture, 81 files
- aspect: request_result_alignment — D1 graded met against c9d9c5a4 by the functional review

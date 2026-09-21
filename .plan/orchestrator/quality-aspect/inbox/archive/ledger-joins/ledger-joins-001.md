envelope_version=1
sender_type=plan
sender_id=ledger-joins
epic=quality-aspect
kind=candidate-lesson
created=2026-09-20T07:24:28Z

# Persist changed_files on every completed task

## Context

The ledger-joins retrospective found per-task change attribution unavailable: only 31 of 33 completed task records carry a changed_files list, so the eligible artifact-emission population was omitted rather than reported over a narrowed subset.

## Root cause

Task close paths do not uniformly persist the changed file list, leaving a mixed recorded/unrecorded corpus that no population rule can measure without silently narrowing it.

## Proposed action

Persist a changed_files list on every completed task record (present-and-empty means measured-no-change) at task close, including finalize-step and late-dispatch closes.

## Evidence

- aspect: logging_gap_analysis — change_attribution unavailable over mixed corpus
- plan: ledger-joins — 31 of 33 completed records carry the list

component: plan-marshall:manage-tasks
category: improvement
title: Persist changed_files on every completed task
confidence: high
source_aspects: logging_gap_analysis

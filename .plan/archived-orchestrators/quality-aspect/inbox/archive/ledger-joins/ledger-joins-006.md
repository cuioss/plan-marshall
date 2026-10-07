envelope_version=1
sender_type=plan
sender_id=ledger-joins
epic=quality-aspect
kind=candidate-lesson
created=2026-09-20T07:31:41Z

component: plan-marshall:phase-6-finalize
category: insight
title: CI wait-budget expiry with later-green re-poll is a standing finalize consideration

## Context

In plan ledger-joins (PR #1545), the ci_complete_precondition wait budget expired
three times while CI was still IN_PROGRESS; each re-poll observed
ci_final_status success at the same HEAD. Four ci_timeout triage findings were
taken_into_account with no action owed (recurrence 4, threshold 2).

## Proposed action

Treat deadline_exceeded as a re-poll signal rather than a failure verdict in
finalize: keep the wait budget tight, always re-poll before triaging, and
resolve the premature timeout findings as taken_into_account once the re-poll
lands green.

## Evidence

- preference-emitter sweep over ledger-joins dispositions: 4 recurrences of
  (phase-6-finalize, triage ci_timeout, taken_into_account)
- enrich target: architecture enrich insight --module plan-marshall

## Provenance

Per-plan preference-emitter sweep at phase-6-finalize of plan ledger-joins;
owed enrich call: architecture enrich insight --module plan-marshall.

envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:20Z

component=plan-marshall:manage-metrics
category=improvement
title=end-phase / phase-boundary: derive the closing token delta from the dispatch-boundary rows instead of a hand-typed flag
source_lesson=2026-11-19-14-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# end-phase / phase-boundary: derive the closing token delta from the dispatch-boundary rows instead of a hand-typed flag

# Candidate lesson: the closing phase token delta is hand-typed from boundary rows and cannot be corrected

- Source signal: plan git-core-incore-write-cas (inbox git-core-incore-write-cas-014), plan-retrospective (plan-efficiency, llm-to-script-opportunities), component `plan-marshall:manage-metrics`, confidence high.
- Evidence: the 5-execute row holds `total_tokens` 941972 against a dispatch-boundary sum of 1329933; the plan's own landing report records the same figure as uncorrectable.

## What happened

One 5-execute close was recorded with `--total-tokens 743` where 742996 was intended (the envelope-2 and envelope-3 dispatch-boundary rows, 365142 + 377854). Explicit flags on a re-entered row are additive deltas and there is no subtract or correct verb, so the typo could not be repaired. The rendered Total is unaffected only because the reconciliation picks the larger boundary measure, which masks the typo instead of catching it. The same row was closed twice ten seconds apart (09:31:55 and 09:32:05) with no intervening work.

## Root cause

The orchestrator transcribes per-dispatch usage figures by hand into `phase-boundary` / `end-phase --total-tokens`, although the same figures are already on disk in `work/metrics-dispatch-boundaries-{phase}.toon`. A hand-copied figure has no plausibility check and no correction path.

## Candidate rule

When `--total-tokens` / `--tool-uses` / `--duration-ms` are omitted on `end-phase` or `phase-boundary`, derive the closing delta from the dispatch-boundary rows recorded since the previous close (the accumulator fallback already does this for finalize), and make the orchestrator workflows omit the flags. Optionally warn when an explicit figure differs from the boundary-row delta by more than an order of magnitude, and offer an explicit correction verb for a re-entered row.

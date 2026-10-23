envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:29Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# Record every finalize step firing in execution_log and the dispatch ledger

## Context

The finalize phase produced 33 `Completed step` work-log lines across 12 distinct steps, with functional-review firing 7 times and code-review 6. The two accounting surfaces recorded far less:

- `execution_log[]` in `execution.toon` holds 21 rows. Code-review never reached it at all despite six firings; the post-rebase re-run between 15:25 and 16:17 (functional-review, code-review, pre-push-quality-gate, ci-verify, automatic-review, sonar-roundtrip) emitted completion lines with no matching `record-step` call.
- `work/metrics-dispatch-boundaries-6-finalize.toon` holds 4 rows against those 33 completions; the whole run has 6 boundary rows.

The consequence is that the retrospective's dispatch audit degrades instead of grading: `dispatch_coverage` reports `dispatched: 0`, `no_evidence: 10` of 12, and `channel_completeness` reports `confidence: low` at ratio 0.212 (7 dispatch lines against 33 completions). On a run where the finalize loop-backs are the main thing worth auditing, the audit could not corroborate anything.

## Root cause

The dispatcher records a step and a dispatch boundary on some branches only — the first firing of a step, and the terminal outcome — and skips both on the internal re-firings a loop-back drives inside one invocation. Because `record-dispatch-boundary` is also called without `--step-id`, every row it does write is keyless, so `firing_comparison` cannot pair a single row even when both sides exist (`keyless_boundary_rows` 1/1/4, `paired_firings` 0 in every phase).

## Proposed action

Make the per-firing record unconditional in the finalize dispatcher: one `record-step` and one `record-dispatch-boundary` per completed step firing, including re-firings, carrying the dispatch's `step_id` on both. The boundary call must forward `--step-id` on every invocation — an omitted flag writes an empty key, which is what makes the pairing inert today. Add a regression assertion that the row count for a phase equals its `Completed step` count.

## Evidence

- aspect: logging_gap_analysis — gaps 1 and 2 (33 completions vs 6 boundary rows / 21 execution rows; all rows keyless).
- aspect: execution-context-dispatch-audit — `dispatch_coverage` 0 dispatched / 2 inline / 10 no-evidence; `firing_comparison` paired_firings 0 for 4-plan, 5-execute and 6-finalize; `channel_completeness.confidence: low`.
- logs/script-execution.log — 26 `record-step` calls and 6 `record-dispatch-boundary` calls against 33 completions.

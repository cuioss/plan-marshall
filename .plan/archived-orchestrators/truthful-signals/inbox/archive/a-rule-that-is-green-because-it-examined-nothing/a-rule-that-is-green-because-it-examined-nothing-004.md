envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:41:02Z

component=plan-marshall:manage-metrics
category=bug
title=Dispatch-boundary context-load columns are always zero and the cause enum is short by five
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing

# Dispatch-boundary context-load columns are always zero and the cause enum is short by five

## Context

Two defects in the same artifact, `work/metrics-dispatch-boundaries-{phase}.toon`.

**Defect 1 — the billing-composition columns are never populated.** `record-dispatch-boundary` declares four per-dispatch context-load flags (`--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens`) and appends them as four columns. Across all **19 rows** this plan recorded — 1 in `4-plan`, 1 in `5-execute`, 17 in `6-finalize` — every one of those four values is `0`. The columns exist; no call site forwards them. Per-dispatch billing composition is therefore not merely unmeasured but unmeasurable from the artifact that exists to carry it.

This matters disproportionately because 6-finalize's 17 rows total **2,895,242 tokens** — 2.01× the entire `metrics.md` plan total of 1,438,440 — and `metrics.md` renders the 6-finalize row as `-`. The dispatch-boundary file is the only place that number exists, and it is the file whose composition columns are blank.

**Defect 2 — the documented cause enum omits the values actually used.** `manage-metrics/SKILL.md` § `record-dispatch-boundary` documents six accepted `--termination-cause` values (`voluntary_checkpoint`, `task_complete_returned_verbatim`, `budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`). The live argparse `choices` accepts **eleven** — adding `step_complete`, `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`. Those five undocumented values account for **18 of this plan's 19 rows** (15 `step_complete`, 1 `task_batch_complete`, plus 2 `error` and 1 `clean_exit_queue_empty` from the documented set).

The two docs in-repo disagree: `plan-retrospective/references/logging-gap-analysis.md` lists all eleven correctly and even instructs consumers to report an explicit zero for each. `manage-metrics/SKILL.md` — the canonical-invocation surface the plugin-doctor analyzer reads — lists six.

## Root cause

Defect 1 is unwired plumbing: the flags were added to the recorder without being threaded through the orchestrator call sites that have the `message.usage` values in hand at dispatch return.

Defect 2 is ordinary doc drift, made sharper by the SKILL.md prose asserting *"missing or unrecognised values are rejected as script errors (there is no implicit fallback)"* — which reads as a closed enum and is true, just of a different, larger set than the one printed beside it.

## Proposed action

- Thread the four `message.usage` fields from each dispatch return into the `record-dispatch-boundary` call at every phase call site, so the four columns carry real values.
- Reconcile `manage-metrics/SKILL.md` § `record-dispatch-boundary` (both the prose and the `## Canonical invocations` block) with the argparse `choices` tuple, and add a derivation guard so the doc cannot drift from `DISPATCH_TERMINATION_CAUSES` again.
- Consider a `dispatch-boundary-summary` verb emitting cross-phase sums and a per-cause histogram — three separate retrospective aspects hand-summed these same rows in this run.

## Evidence

- aspect: dispatch_boundaries — 19/19 rows with `input_tokens=0 output_tokens=0 cache_read_input_tokens=0 cache_creation_input_tokens=0`; 6-finalize total 2,895,242
- aspect: logging_gap_analysis — the DISPATCH_TERMINATION_CAUSE rule is scoped to the 5-execute file alone, so it graded 1 of the 19 rows and never saw the two `error` terminations in 6-finalize
- source: `record-dispatch-boundary --help` shows 11 choices; `manage-metrics/SKILL.md` documents 6

envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=candidate-lesson
created=2026-08-23T22:09:08Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=cloud-lane-build-gate-reads-one-field-short
source_aspects=logging_gap_analysis,execution_context_dispatch_audit

# check-dispatch-audit grades channel confidence from a denominator the re-fires inflate

## Context

`check-dispatch-audit` emitted:

```
channel_completeness:
  dispatch_line_count: 15
  completion_count: 23
  dispatched_step_count: 7
  ratio: 0.652
  confidence: nominal
```

The `completion_count: 23` counts `[STEP] Completed step` lines. At least 4 of those are the
unpaired re-fire duplicates documented in the sibling candidate-lesson (create-pr,
pre-push-quality-gate, automatic-review, ci-verify). Excluding them moves the ratio from 0.652
to roughly 0.79.

## Root cause

`channel_completeness` treats the completion-line count as a proxy for the number of step
executions. That proxy holds only while the `[STEP]` bracket is balanced. It is not, on any plan
whose head-dependent gates re-fire — and re-firing is the designed behaviour, not an anomaly.

This is the audit's own confidence signal, so the contamination is self-referential: the
component whose job is to report whether the dispatch channel is complete is grading itself
against an inflated denominator, and it reported `nominal`.

## Proposed action

Derive the completion population from `status.metadata.phase_steps` — which already carries
`firing_count` and `prior_firings[]` per step and is the authoritative record — rather than from
log-line counts. If the log-line count is kept, deduplicate by step name and publish both the raw
and the deduplicated figure so the ratio's population is legible.

Note this is a *population-derivation* defect of exactly the archetype the epic already tracks:
a set-guarding metric whose population is counted from a surface that can double-count.

## Evidence

- aspect: execution_context_dispatch_audit — `ratio: 0.652`, `confidence: nominal`
- aspect: logging_gap_analysis — the 4 unpaired completions with timestamps
- `status.json` carries `firing_count` for each re-fired step, so the correct denominator was
  already available on disk

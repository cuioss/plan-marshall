envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:59:48Z

component=plan-marshall:plan-retrospective
category=bug

# script-failure-analysis emits a lessons[] block that no downstream aspect consumes

The `script-failure-analysis` aspect computes and publishes a `lessons[]` array — 11 entries in this
run, each with `component`, `category`, `title`, `subtype`, `occurrence_count`. Nothing reads it.

## Observed

In this plan's `quality-verification-report.md`:

- `script-failure-analysis` reported `total_failures: 16`, `unique_failures: 11`, and an 11-entry
  `lessons[]` array.
- `lessons_proposal` synthesized **8 proposals**. Their `source_aspects` fields name
  `manifest_decisions`, `logging_gap_analysis`, `plan_efficiency`, `outline_vs_shipped`,
  `artifact_consistency`, `routing_decisions`, and `request_result_alignment`.
- **`script-failure-analysis` appears in no proposal's `source_aspects`.** Zero of the 11 computed
  lesson candidates reached the epic inbox.

Every one of the aspect's own findings was emitted at `[INFO]` severity, so the report's headline
band shows eleven bare `- [INFO]` bullets with empty message text — the section renders as visually
empty while carrying the run's entire script-failure signal.

## Why it matters here specifically

The dispatcher's Signal Gate treats `signal_script_failure_clusters_count` as one of three
independent lesson-bearing triggers. In this run it was **9** — the largest of the three signals by
distinct-notation count. A trigger that fires the step and then contributes nothing to the step's
output is a signal that reports work it did not cause.

## Rule

Either wire `script-failure-analysis.lessons[]` into `lessons_proposal` as a source population, or
stop computing it. A producing aspect whose output has no consumer should not publish a field named
`lessons` — a reader (and the `compile-report` bundle) cannot distinguish "computed and routed" from
"computed and dropped". If the drop is deliberate, the aspect must say so in the field name or carry
an explicit `routed: false` discriminator.

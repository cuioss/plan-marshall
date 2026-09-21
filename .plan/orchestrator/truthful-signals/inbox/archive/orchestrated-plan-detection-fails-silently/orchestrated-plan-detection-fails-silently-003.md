envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:41:18Z

component=plan-marshall:phase-3-outline
category=bug
bundle=plan-marshall

# Light lane leaves references.json without track and affected_files, and phase-4-plan silently falls back instead of reporting

## What happened

The same light-lane collapsed envelope on PLAN-114 left `references.json` without a `track` field and without `affected_files`. `phase-4-plan` reported `field_not_found` for both and **continued via fallbacks**. The run went green.

## Why it matters for truthful signals

This is the softer, more dangerous sibling of the `pr_title` failure recorded alongside it. There, the consumer had no fallback, so the omission announced itself as a hard `pr_title_missing`. Here the consumer *did* have a fallback, so the run proceeded on **defaulted rather than authored values** — an unstated `track` and an empty `affected_files` — and nothing in the run's output distinguished that from a properly-authored run.

That is exactly the confident-signal-hides-a-caveat shape: the phase reported success, and the caveat ("I planned against defaults because the inputs were absent") was consumed only by the fallback branch and never surfaced.

## Corrective rule

Two parts, both required:

1. **Producerless-consumer sweep** — same as the `pr_title` case: re-home the `track` and `affected_files` writes into the light lane, or declare them optional in the light lane's contract.
2. **A `field_not_found` fallback in a phase skill MUST log at WARNING naming the missing field.** A fallback that fires silently makes a defaulted run indistinguishable from an authored one. The fallback may keep the run alive; it may not keep the run quiet.

## Recurrence signature

Any `field_not_found` → default-value branch in a phase workflow with no accompanying WARNING emission. Grep the phase skills for fallback prose that reads "if absent, use …" without a paired log line.

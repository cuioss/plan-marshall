envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T10:34:13Z

component: plan-marshall:phase-6-finalize
category: improvement
title: Owed architecture insight — ci-timeout standing consideration in plan-marshall:phase-6-finalize

# Owed architecture hints: preference-emitter, plan implement-plan-lb-60-lb-40-regression-fixes

The per-plan preference-emitter promoted one within-plan `taken_into_account`
recurrence (2 occurrences) to an owed `architecture enrich` insight. It is
recorded here as a follow-up rather than written, because this step is
`post_run_review: true` and runs after the merge gate (writing tracked
`enriched.json` source on `main` post-merge is unpublishable).

## Owed enrich call

- target module: `plan-marshall:phase-6-finalize`
- enrich verb: `insight` (the `taken_into_account` disposition generalizes to an insight)
- verbatim generalized hint text:

  the project treats [ci_timeout] verify / verify failed as a standing consideration in plan-marshall:phase-6-finalize

## Command

```text
architecture enrich insight --module plan-marshall:phase-6-finalize \
  --insight "the project treats [ci_timeout] verify / verify failed as a standing consideration in plan-marshall:phase-6-finalize"
```

## Provenance

Promoted from findings `5f9dbe` and `5b8b4c` (both `taken_into_account`) on the
just-finished plan. Both record a `verify / verify` CI check that was still
running when the bounded `ci-complete` wait expired; the check later concluded
SUCCESS on the same HEAD, so no code defect existed. The pattern is a standing
infrastructure-timeout consideration for that module, not a per-run defect.

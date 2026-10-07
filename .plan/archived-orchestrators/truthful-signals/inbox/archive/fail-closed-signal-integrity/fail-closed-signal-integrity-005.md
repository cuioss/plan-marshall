envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T21:10:30Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# scope_creep_check reports a benign verdict when it has no baseline SHA

`scope_creep_check` returned `no_baseline_sha` — it had nothing to diff against — and
alongside it reported `residual_count: 0` and `finding_emitted: false`. The two halves of
the payload disagree: the reason field says "I could not measure", the verdict fields say
"I measured and found nothing wrong".

Downstream reads the verdict fields. A check that could not run therefore passes as a check
that ran clean.

Observed live in this run's finalize, on merged main.

## Impact

Scope creep goes unreported whenever the baseline SHA is unavailable, and the finalize
summary shows a clean scope gate. This is the same archetype as the `restore-from-plan` and
review-retrospective defects filed from this run — three independent instances of
"could-not-measure rendered as measured-clean" inside finalize alone.

## Solution

When the baseline SHA is absent, the verdict fields must not be populated with the
measured-clean values. Either:

- omit `residual_count` / `finding_emitted` entirely and let the absence be the signal, or
- carry an explicit `measured: false` discriminator that every consumer of the verdict must
  branch on.

A zero that means "could not look" and a zero that means "looked, found nothing" must not
share a representation — the `inbox list` `inbox_state` discriminator is the in-repo
precedent for the correct shape.

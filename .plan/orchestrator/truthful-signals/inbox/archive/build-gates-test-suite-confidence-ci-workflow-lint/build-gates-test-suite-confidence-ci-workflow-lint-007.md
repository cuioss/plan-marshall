envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:52:53Z

kind=candidate-lesson
source=finalize-step-preference-emitter
plan=build-gates-test-suite-confidence-ci-workflow-lint
owed_enrich_module=plan-marshall
owed_enrich_verb=insight

# Owed architecture hint — a correct reviewer finding may be accepted rather than fixed in-run

A `(module=plan-marshall, finding-class=pr-comment, disposition=accepted)`
recurrence cleared the per-plan threshold (3 occurrences, threshold 2). Only
comments attributed to a recognized reviewer bot were counted.

**Owed call** — to be issued after merge, per the discover-after-merge rule:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module plan-marshall \
  --insight "The project tolerates accepting a correct review-bot finding in plan-marshall without fixing it in the same run, when the finding is a latent drift risk rather than a wrong verdict reachable at the current HEAD, and when fixing it would decide a design fork better settled once across every affected site than per-site under merge pressure."
```

Generalized, not transcribed, per
`phase-6-finalize/standards/disposition-to-hint-routing.md` § (c).

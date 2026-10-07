envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:52:55Z

kind=candidate-lesson
source=finalize-step-preference-emitter
plan=build-gates-test-suite-confidence-ci-workflow-lint
owed_enrich_module=plan-marshall
owed_enrich_verb=insight

# Owed architecture hint — anti-pattern findings are recorded as standing concerns

A `(module=plan-marshall, finding-class=anti-pattern, disposition=taken_into_account)`
recurrence cleared the per-plan threshold (3 occurrences, threshold 2).

**Owed call** — to be issued after merge, per the discover-after-merge rule:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module plan-marshall \
  --insight "The project treats anti-pattern findings in plan-marshall as standing concerns recorded against the corpus rather than as in-run blockers: the anti-patterns it detects are recurrence classes whose remedy is a rule applied across many sites, so an instance is expected to be recorded and generalized rather than fixed where it was found."
```

Generalized, not transcribed, per
`phase-6-finalize/standards/disposition-to-hint-routing.md` § (c).

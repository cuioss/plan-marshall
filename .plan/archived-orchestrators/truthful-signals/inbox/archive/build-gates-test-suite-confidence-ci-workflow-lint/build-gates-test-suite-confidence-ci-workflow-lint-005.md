envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:52:49Z

kind=candidate-lesson
source=finalize-step-preference-emitter
plan=build-gates-test-suite-confidence-ci-workflow-lint
owed_enrich_module=plan-marshall
owed_enrich_verb=insight

# Owed architecture hint — improvement findings are a standing consideration in plan-marshall

A `(module=plan-marshall, finding-class=improvement, disposition=taken_into_account)`
recurrence cleared the per-plan threshold (6 occurrences, threshold 2).

**Owed call** — to be issued after merge, per the discover-after-merge rule:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module plan-marshall \
  --insight "The project treats improvement findings as a standing consideration in plan-marshall rather than as defects to fix in the run that surfaces them: they are recorded with rationale and folded into later work, so an improvement raised mid-plan is expected to be closed as considered rather than either fixed or dropped."
```

Generalized, not transcribed: no per-finding hash ids, titles, or raw disposition
rows are carried here, per the privacy invariant in
`phase-6-finalize/standards/disposition-to-hint-routing.md` § (c).

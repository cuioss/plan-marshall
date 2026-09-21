envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:52:51Z

kind=candidate-lesson
source=finalize-step-preference-emitter
plan=build-gates-test-suite-confidence-ci-workflow-lint
owed_enrich_module=plan-marshall
owed_enrich_verb=insight

# Owed architecture hint — reviewer comments are folded in rather than each fixed

A `(module=plan-marshall, finding-class=pr-comment, disposition=taken_into_account)`
recurrence cleared the per-plan threshold (4 occurrences, threshold 2). Only
comments positively attributed to a recognized reviewer bot were counted, per the
authorship-admissibility gate — the pipeline's own control traffic was excluded.

**Owed call** — to be issued after merge, per the discover-after-merge rule:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module plan-marshall \
  --insight "The project treats a large share of external review-bot comments in plan-marshall as standing considerations rather than per-comment defects: a meaningful fraction of every bot review is status or meta traffic, so a reviewer's comment count is not a defect count and triage is expected to close many comments as considered."
```

Generalized, not transcribed, per
`phase-6-finalize/standards/disposition-to-hint-routing.md` § (c).

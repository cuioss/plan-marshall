envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:02:59Z

# Candidate lesson: two of eight non-run paths reached a "green" report with the work un-run

- source_signal: qgate / 5-execute (D1 gate verdict)
- record_id: 4294eb
- component: plan-marshall:phase-6-finalize
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md
- resolution: taken_into_account — drove the new DEGRADED display_detail variant

## What happened

The Branch A non-run list had exactly eight members. Named detail variants existed for three. The two branch-0 module-tests degradation paths — "the resolved build skill exposes no resolve-test-scope verb" and "no module-tests canonical resolves at all" — carried NO named variant and only directed the composer to Mark Step Complete (Success). Both therefore reached Branch A with module-tests un-run while the default detail ended "module-tests green".

## Candidate rule

Every degradation path needs its own honest report string. A degradation path that falls through to the success composer inherits the success message and turns an un-run gate into a reported green — the highest-severity shape of the false-signal family, because every downstream consumer reads it as evidence.

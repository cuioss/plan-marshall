envelope_version=1
sender_type=plan
sender_id=antigravity-execution-fidelity
epic=live-blockers
kind=candidate-lesson
created=2026-10-14T21:24:15Z

title: Owed architecture hint — triage-workflow review comments treated as standing consideration
module: plan-marshall
enrich_verb: insight
enrich_command: architecture enrich insight --module plan-marshall
source_plan: antigravity-execution-fidelity
pattern: (plan-marshall, coderabbit inline review comments on the triage workflow, taken_into_account) recurring 2x within the plan

## Owed hint

The project treats coderabbit inline review comments on the triage workflow
as a standing consideration in plan-marshall: repeated review observations
about the triage workflow's wording and contracts are folded into the work
as standing concerns rather than fixed one by one. A future outline in this
module should budget for that triage loop instead of treating each such
comment as a novel defect.

## Reconstruction

To apply: run `architecture enrich insight --module plan-marshall` with the
hint text above. Do not re-derive the pattern from finding dispositions;
`archive-plan` moves the disposition corpus. No per-finding identifiers are
recorded here by the privacy invariant.

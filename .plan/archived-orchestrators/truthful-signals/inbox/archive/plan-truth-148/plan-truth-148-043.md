envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:17Z

# Candidate lesson: a deliverable declared a module the inventory does not attribute its file to

- source_signal: qgate / 3-outline (architecture constraint)
- record_id: a3510c
- component: solution-outline-deliverable-10
- file: doc/concepts/automatic-reviews.adoc
- resolution: taken_into_account — left as declared; the divergence cost nothing in this run

## What happened

Deliverable 10 declared `module: plan-marshall`, but its only written file resolves via `which-module` to `module: documentation`. The deliverable carried an operator decision recorded on the DOMAIN axis only, which says nothing about the module field. Downstream consumers that read `module` rather than `domain` — the phase-4-plan module-mapping validator, execution-manifest scoping, and module-scoped build resolution — would resolve the wrong module.

Corroborating evidence from the same run: `pre-push-quality-gate` logged "Footprint paths resolved to no registered module: doc/concepts/automatic-reviews.adoc -- proceeding whole-tree; scoped coverage for these paths is not determinable" on every single firing.

## Candidate rule

`domain` and `module` are separate axes and an operator decision on one does not settle the other. Resolve a deliverable's `module` from `which-module` on its written files, and when a written path resolves to no registered module, treat the resulting whole-tree fallback as a declared cost rather than an incidental one.

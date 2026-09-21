envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:59:13Z

# Candidate lesson: the governing contract source still documented the retired closing rule

- source_signal: qgate / 6-finalize
- record_id: bf6e76
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:159
- resolution: fixed (row replaced by a pointer to the workflow doc's Step 4)

## What happened

The change rewrote how the step closes, but `phase-6-finalize/SKILL.md`'s Built-in Step Dispatch Table row still said the step "records done on a full-surface clean pass". SKILL.md is a declared contract source for the modified workflow doc, and it was NOT in the plan's diff, so the drift was unswept. The dispatcher reads that row to understand the step it is routing.

## Candidate rule

A file's declared `contract_sources` are part of the change footprint even when they carry no edit in the diff. Sweep them on every behavioural change, and close the drift by POINTING at the authoritative statement rather than restating it in the table row.

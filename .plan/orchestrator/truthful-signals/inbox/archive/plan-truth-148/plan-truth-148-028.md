envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:48Z

# Candidate lesson: a supporting doc still declared itself a step that had been retired

- source_signal: qgate / 6-finalize
- record_id: 6e75ce
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/validation.md:172
- resolution: fixed in commit dafe97834 — the section was deleted; verified by a content sweep returning 0 occurrences over 5462 inventoried files with clean coverage

## What happened

`validation.md` still carried a "Mark Step Complete" section invoking `mark-step-done --step validation` — for a step this same plan had already retired from `required-steps.md`, `output-template.md` and the SKILL.md worked example. The document carries no step frontmatter and the ext-point classifies it an excluded supporting doc, so it was never a step at all.

## Candidate rule

The retirement population includes SUPPORTING docs, not just registered step docs: a doc with no step frontmatter can still contain a live step invocation an agent will execute. Derive the sweep from the retired identity's name across the whole inventory, and report the sweep's coverage fields so a zero is trustworthy.

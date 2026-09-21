envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:40Z

# Candidate lesson: the fix for a drifting list introduced a NEW list missing 7 of 18 members

- source_signal: qgate / 6-finalize
- record_id: 7d57d0
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md:143
- resolution: fixed by DELETION — replaced with a pointer at each step's own `order:` frontmatter

## What happened

Round 6 "fixed" the drifting order list (finding 7bdcff) by writing a hand-maintained 11-row list under a completeness-implying authority citation. Seven of the eighteen `default_on` finalize steps were absent from it. The corrective action reproduced the defect class it was correcting, and made it worse by adding an authority claim.

## Candidate rule

This is the highest-value recurrence in the run: a fix for a hardcoded-mirror defect that writes a new hardcoded mirror. When the finding is "this list must mirror a set defined elsewhere", the only admissible fixes are (a) derive it at build/run time or (b) delete it and point. Writing a fresh, hand-checked copy is not a fix — and attaching an authority citation to it converts a stale list into a vacuous-authority generator.

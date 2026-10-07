envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:35Z

# Candidate lesson: a hand-maintained step-order list disagreed with the live derivation

- source_signal: qgate / 6-finalize
- record_id: 7bdcff
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md:137
- resolution: fixed — the copy was deleted and replaced by a pointer at each step's own `order:` frontmatter

## What happened

The Placement block carried a canonical default step order that disagreed with what `find_implementors` actually returns (architecture-refresh=10, push=11, create-pr=20, ci-verify=22, automatic-review=30, sonar-roundtrip=40, branch-cleanup=70, lessons-capture=991, record-metrics=998, archive-plan=1100).

## Candidate rule

A list that must mirror a set defined elsewhere is a defect unless it is derived from that source at build or run time. The remedy is deletion plus a pointer at the deriving source — not correcting the copy, which only resets the drift clock.

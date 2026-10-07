envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:10Z

# Candidate lesson: an equality assertion compared a whole header string against a narrower derivation

- source_signal: qgate / 5-execute (test-failure)
- record_id: cf4a33
- component: (test) test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py
- resolution: fixed via TASK-019

## What happened

`test_roster_correctness_coverage_is_reported_not_asserted_shut` failed because the published coverage header had gained a new clause (the dispatch-site population) while the live derivation it was compared against had not. The assertion compared the WHOLE header string, so appending an honest new clause to the header broke an equality that was only ever meant to check the coverage clause. Surfaced only by the orchestrator-tier whole-tree run: 25948 passed, 1 failed.

## Candidate rule

An equality assertion over a composed human-readable string breaks whenever the string legitimately grows. Compare the specific clause the invariant is about, or compare structured fields — otherwise every honest improvement to a report header registers as a regression, which trains the next author to stop enriching the header.

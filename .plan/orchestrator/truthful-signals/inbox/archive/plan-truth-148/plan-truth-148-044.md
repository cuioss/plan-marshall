envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:20Z

# Candidate lesson: the note that establishes file-overlap sequencing relied on the sequencing it establishes

- source_signal: qgate / 3-outline
- record_id: d8caab
- component: solution-outline-approach
- file: test/plan-marshall/phase-6-finalize/test_pre_submission_self_review_verdict.py
- resolution: taken_into_account — harmless in execution because deliverable 9 carried `depends: 1, 8`

## What happened

Approach item 5 presented itself as THE enumeration of file overlaps that must be sequenced, and was incomplete in one direction and wrong in the other. Omitted: a test file declared as a write target by BOTH deliverable 8 and deliverable 9 — the note listed no test-file overlap at all. Wrong entry: it named a reader (deliverable 3) that declares no such file.

The circularity is the sharp part: the omission was harmless ONLY because deliverable 9 carried a `depends` edge — and the note is the document that is supposed to establish that edge, so it cannot lean on it.

## Candidate rule

An overlap enumeration must be derived by set intersection over every deliverable's declared write targets, in both directions, and it cannot cite as mitigation the dependency edges it is itself responsible for justifying.

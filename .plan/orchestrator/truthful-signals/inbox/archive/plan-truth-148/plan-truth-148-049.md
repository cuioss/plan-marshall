envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:36Z

# Candidate lesson: a test treated a table marking as proof that a consumer exists

- source_signal: automatic-review / CodeRabbit inline (PR #1488), severity Major
- record_id: 44e446 (comment PRRC_kwDOQ3xasM7uheEA)
- file: test/plan-marshall/extension-api/test_extension_discovery_behavior.py:730
- resolution: fixed via TASK-025

## What happened

The test treated the literal text `Conditional` / `Optional` / `Never` in a documentation table as proof that a consumer reads the field. If a new field is marked `Optional` and no parser, dispatcher, or other consumer reads it, the test still passes.

The sharp part is the history: this run's OWN self-review (finding a9de78) had already refuted the underlying premise by complete-coverage sweep — `advances_main_via_rebase` has no Python consumer at all. The document's universal claim was narrowed in response, and the sibling TEST encoding the identical refuted premise was left standing until a review bot caught it.

## Candidate rule

Prose, a code comment, or a summary table is not a mechanism. And when a premise is refuted, the remediation population is every artefact that encodes it — document AND test. Fixing the document alone leaves a live green guard asserting the thing that was just disproved, which is strictly worse than no guard.

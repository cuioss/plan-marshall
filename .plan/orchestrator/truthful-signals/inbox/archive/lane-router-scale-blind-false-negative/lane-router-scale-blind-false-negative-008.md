envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:50:04Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# `github_pr post_responses` is not idempotent — it re-transmitted 9 duplicate thread replies on the second triage

A second triage pass over the same PR re-sent **9 replies that had already been posted**,
producing duplicate threads on PR #1068. The verb has no record of what it already
transmitted, so every invocation re-posts the full disposition set.

The comparison inside our own codebase makes this unambiguous: **`sonar post_responses`
tracks a responded marker** and is therefore idempotent across repeated triage passes.
`github_pr post_responses` implements the same conceptual verb without the marker. Two
providers of one abstraction, differing on a property that the abstraction's callers
reasonably assume holds.

Loop-backs make repeated triage the normal case, not an edge case — any plan that
re-enters triage after a fix will duplicate its entire prior response set.

## Solution

Give `github_pr post_responses` the same responded-marker mechanism `sonar
post_responses` already has: record per-finding transmission, and skip a finding whose
response was already posted. On a repeat invocation the verb should report how many were
skipped as already-responded, so the idempotency is observable rather than assumed.

More generally: when two providers implement one abstraction, an idempotency guarantee
held by one and not the other is a defect in the abstraction, not a provider quirk.
Callers cannot branch on which provider they got.

## Impact

Affects every loop-back that re-runs PR triage. Duplicate replies also pollute the very
review threads later runs read as evidence, so the defect degrades the review-ingest
signal in addition to being noisy.

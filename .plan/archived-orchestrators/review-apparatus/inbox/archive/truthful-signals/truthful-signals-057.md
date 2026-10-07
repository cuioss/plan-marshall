envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-13T20:53:19Z

# Two review-measurement defects from PLAN-TRUTH-127's landing (PR #1483)

source_plan: plan-truth-127
source_pr: 1483
source_epic: truthful-signals

Forwarded from `plan-truth-127`'s candidate-lesson `inbox/plan-truth-127-003.md` (instance 2,
explicitly flagged by the plan itself as review-apparatus's by the standing three-way routing
rule) and from the landing's own residue. Kept as a shared-archetype lesson in truthful-signals
too (`2026-09-13-20-004`) — this is the review-mechanics half.

## 1. The status-summary carve-out cannot fire on the real record shape

`review_retrospective._is_status_summary` delegates to `review_gate_delta.is_status_summary`,
which matches the registry's `review_body_summary_patterns` against
`_BODY_FIELDS = ('body', 'message')`. Every `pr-comment` record in this plan's store carries
the comment text ONLY under the quarantined `raw_input.body`; no top-level `body` was promoted.
With nothing to match, both of CodeRabbit's "Actionable comments posted: N" `review_body`
records were classified **actionable** rather than meta. On PR #1483 that landed on the correct
side by accident (both bodies also carried a real finding), but the mechanism is not the
documented one, and on a PR whose status summary is purely a summary the same path inflates
`actionable_count` by one per review round.

Proposed action: either promote a top-level `body` on the ingest path, or make `_BODY_FIELDS`
reach `raw_input.body`. Add a positive test built from a REAL stored record rather than a
hand-constructed fixture — a fixture that happens to carry a top-level `body` is what let this
pass unnoticed.

## 2. A round-2 Medium scored as meta purely because it arrived as a comment reply

From the review retrospective: the status-summary carve-out issue above is one of "two defects
in the measuring apparatus itself." The second: a round-2 Medium finding was scored as meta
solely because it arrived as a comment reply rather than an inline note — the classifier keys
on comment SHAPE (inline vs. reply) rather than content, so a substantive reply-form finding is
mis-classified regardless of what it says.

Evidence: review-retrospective.md § "Instrument Observations" (PLAN-TRUTH-127, PR #1483,
`8ff2c2` verified in full for item 1; round-2 Medium comment-reply mis-classification per the
same retrospective).

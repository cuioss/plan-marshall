envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T09:06:07Z

component=plan-marshall:workflow-integration-github
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# Bot STATUS bodies are filed as pending findings and block the pre-merge comment barrier

## Context

The `pr-comment` producer filed review-bot **status** bodies as pending findings in both
review iterations of this run. The bodies carried no review content — they were an
approval notice, a "Review finished" marker, and an "Actionable comments posted: N"
header.

Each one then had to be hand-disposed before the pre-merge comment barrier would let the
merge proceed. The barrier is designed to hold on unhandled reviewer feedback; here it
held on a bot announcing that it had finished, twice.

The cost is not only the manual dispositions. A barrier that routinely stops on
non-findings trains the operator to clear it without reading, which is precisely the
habit the barrier exists to prevent.

## Root cause

The producer already has the machinery for this: the registry declares per-bot
`contentless_review_markers` and `actionable_content_markers`, and a content-aware layer
consumes them. The layer is **per bot**, and it only fires for a bot that declares the
lists. `sourcery.md` states plainly that this bot "declares neither
`contentless_review_markers` nor `actionable_content_markers`, so the producer's
content-aware layer never fires for it — the empty list is the fail-closed default".

Fail-closed is the right default for a finding COUNT (better to over-count than to drop a
real finding). But the same default routed through the pre-merge barrier turns every
undeclared bot's status body into a merge-blocking item, so the conservative choice in
one consumer becomes an operational stall in another.

`dfabe3d8` (#1344) closed the **refusal** leg — an unmatched refusal is now classified
and skipped rather than filed. The other two legs are untouched: an approval **verdict**
and an action-performed **status line** are neither refusals nor review content, and both
still slip through as pending findings.

## Proposed action

Two candidate directions, worth deciding between rather than combining blindly:

1. Populate `contentless_review_markers` for the bots that currently declare none, so the
   existing content-aware layer fires. Cheapest, but it is an enumeration that will fall
   behind the way the refusal-pattern list did.
2. Make the BARRIER, not the producer, the place the distinction is drawn: a finding whose
   body matches no actionable-content shape should not count toward the unhandled total
   even if it was filed. The store keeps the record; the gate stops holding on it.

The second is the more durable shape, because it stops the barrier depending on an
enumeration staying complete.

## Evidence

- observed in BOTH review iterations of this run; each required hand disposition to clear the barrier
- filed bodies were: an approval notice, "Review finished", "Actionable comments posted: N"
- `automatic-review/standards/sourcery.md` — declares neither marker list, so the
  content-aware layer never fires for that bot
- `dfabe3d8` (#1344) "classify unmatched refusals, skip filing them" — the refusal leg only

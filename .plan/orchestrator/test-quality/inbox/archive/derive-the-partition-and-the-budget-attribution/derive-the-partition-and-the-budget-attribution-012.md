envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T09:06:03Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# Sourcery's third refusal phrasing matches no registry pattern, so a refusal read as participation

## Context

Sourcery declined to review this PR with a notice of the form:

> you've used your own review budget of N diff characters

That refusal matched none of the configured detectors, so the bot was not resolved to
`refused` — its comment was treated as ordinary participation. A reviewer that declined
to look was recorded as a reviewer that looked.

This is the failure mode the bot-participation contract is built to prevent: the whole
point of the refusal branch is that non-participation must be visible at the merge gate,
where the remaining options are expensive. An unrecognised refusal converts a known gap
into an unknown one.

## Root cause

Verified mechanically against the configured patterns. `sourcery.md`'s registry block
declares exactly two `refusal_patterns`:

- `your pull request is larger than the review limit of` (the per-PR size ceiling, #1014)
- `reached your weekly rate limit of` (the account-level weekly quota, #1034 / #1037)

The observed notice is a **used-your-budget** statement, not a larger-than or a
reached statement, so it matches neither. The structural last-resort recogniser
(`_github_pr._is_rate_limit_notice`) keys on exceeded / reached / hit phrasing, and
"you've used your own review budget of" is none of those — so the fallback is blind to it
for the same reason the doc already records the fallback being blind to the size ceiling.

The doc states "Sourcery has at least TWO observed refusal phrasings, so the structural
recogniser must not be assumed to cover this bot". There are now three, and the sentence
is the warning that the pattern list is an enumeration of what has been seen rather than
a closed set.

`dfabe3d8` (#1344) is adjacent but does not close this: it classifies **unmatched**
refusals and stops them being filed as findings. That handles a refusal already
recognised as one; it does not make this phrasing recognised.

## Proposed action

Add the third phrasing to sourcery's `refusal_patterns`, handle-free and number-free in
the same style as the existing two (e.g. `used your own review budget of`). Classify its
CAUSE: a per-account diff-character budget is a quota, not a diff-size ceiling, so it
belongs OUT of `refusal_size_patterns` and keeps the `refused_hard` awaitability member —
the same placement the weekly quota already has.

More durably: an unmatched comment from a registered bot that files zero findings is
itself a signal that the pattern list has fallen behind. Surfacing that as an
`unrecognised_refusal` observation, rather than as silent participation, is what stops
the fourth phrasing costing another run.

## Evidence

- observed notice: "you've used your own review budget of N diff characters"
- `automatic-review/standards/sourcery.md` registry block — `refusal_patterns` holds
  exactly the two phrasings above; verified mechanically against the configured set
- `_github_pr._is_rate_limit_notice` keys on exceeded / reached / hit, which this notice is not
- `dfabe3d8` (#1344) covers the unmatched-refusal FILING leg, not the recognition leg

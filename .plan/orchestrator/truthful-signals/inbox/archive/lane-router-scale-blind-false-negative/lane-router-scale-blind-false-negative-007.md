envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:49:59Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# `fetch_findings` dedups on `comment_id`, so an edited-in-place bot comment is dropped — participation credited, content lost

`pr-agent` **edits its existing comment in place** rather than posting a new one when it
updates a review. `fetch_findings` deduplicates against already-seen `comment_id`s, so
on the second fetch the comment matched a known id and was skipped — even though its
body had **materially changed** and carried new findings.

The failure mode is the worst-shaped one available:

- The comment was seen, so the bot was **credited with participation**.
- The changed body was dropped, so its **content never entered the ledger**.
- Nothing reported an anomaly — the fetch succeeded, the counts looked plausible, and
  the review appeared complete.

The new findings were recovered only **by hand**, after a human noticed the body did not
match what had been triaged.

## Solution

Dedup on **content identity, not comment identity**. Store a body hash alongside
`comment_id`; a known `comment_id` whose body hash differs is a NEW observation and must
be filed, not skipped. The edit-in-place case is not exotic — it is the normal update
mechanism for at least one required reviewer.

Related: a re-fetch that finds a changed body should say so explicitly, so an editing bot
is visibly distinguishable from a silent one.

## Impact

Affects every review bot that updates its comment in place rather than appending a new
one. Sharpens the standing rule that a comment *from* a bot is not a review *by* it: this
adds that even a correctly-attributed comment can be silently stale in the ledger while
the live comment carries different content.

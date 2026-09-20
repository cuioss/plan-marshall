envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T18:39:55Z

category=insight
component=plan-marshall:automatic-review
title=A published ETA beats a configured wait floor

## What happened

PLAN-TRUTH-125's finalize was gated on a mandatory CodeRabbit review. The bot
refused three times with a rate-window notice. The operator's standing protocol
said: wait at least 90 minutes, retry, up to 10 waits.

Rounds 5, 6 and 7 were each roughly 1h45m apart. **All three refused.** A rolling
hourly window does not explain that.

Round 7's refusal notice — CodeRabbit's summary comment, edited in place 11
seconds after the trigger — stated its own reset:

```text
[!WARNING] Review limit reached
Next included review available in 21 minutes.
You've used all free OSS reviews for now.
```

A retry timed to that stated ETA (round 8, ~2 minutes past the reset) succeeded on
the first attempt and produced the review that unblocked the merge.

## The lesson

When a refusing service publishes its own reset time, **read it off the notice
body and time the retry to it**, rather than applying a configured floor. The
floor was set without knowledge of the ETA; it was not wrong so much as
uninformed, and it cost roughly five hours of unattended wall-clock against a
21-minute window.

Two corollaries, both of which bit here:

- **Do not trust the extracted field over the body.** `refusal_eta` came back
  empty on every round because none of the three registered
  `rate_limit_eta_patterns` matches the leading `Next included review available in
  N minutes` phrasing — they all anchor on trailing clauses. The ETA was published
  and unread. See the sibling proposal on guarding extraction lists.
- **Distinguish refusing from not reacting.** These are different operator
  remedies (wait vs. close-and-reopen the PR). CodeRabbit reacted within 5-11
  seconds of every trigger, which is positive evidence of a refusal rather than
  silence — establish that by timestamp comparison before choosing the remedy.

## How to apply

Before spending a configured wait, check whether the refusal names its own reset.
If it does, that number is the wait. If the tooling reports no ETA, read the
comment body before believing it.

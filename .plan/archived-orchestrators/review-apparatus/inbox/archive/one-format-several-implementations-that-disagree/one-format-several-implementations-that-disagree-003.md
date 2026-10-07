envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T18:40:23Z

category=anti-pattern
component=plan-marshall:automatic-review
title=Guard the EXTRACTION list, not only the DETECTION list

## The shape

A paired detect-then-extract design has two lists:

- a **detection** list that decides *whether* a notice is a refusal
  (`refusal_patterns`), and
- an **extraction** list that pulls a value *out of* the recognised notice
  (`rate_limit_eta_patterns`).

`refusal_patterns` has a drift detector: an unrecognised refusal is reported via
`refusal_pattern_drift[]` and `unrecognised_refusal[]`, and the latter is
state-determining rather than advisory. **`rate_limit_eta_patterns` has nothing.**

## Why that asymmetry is silent

Observed on PR #1427 across three review rounds. CodeRabbit's free-OSS notice
states `Next included review available in 21 minutes`. All three registered
extraction regexes anchor on a trailing clause the notice does not carry
(`before requesting another review`, `before … limit resets`). So:

1. **Detection succeeded.** `Review limit reached` matched cleanly, so no drift
   record fired — correctly, by that detector's own contract.
2. **Extraction silently yielded nothing.** `refusal_eta: ""`.
3. **The empty value is documented as legitimate.** `coderabbit.md` § "Rate-limit
   class" says a notice stating no ETA "yields an empty `eta`, which the caller
   reports as unknown rather than as 'reopens now'". So the failure mode is
   spelled as intended behaviour, and an operator reading "ETA unknown" has no way
   to tell *the notice stated none* from *we could not parse the one it stated*.
4. **It is load-bearing.** `review_rate_window_await` derives `--window-seconds`
   from this field.

Cost on the observed run: roughly five hours of unattended waiting against a
21-minute window the bot had already published.

## The generalisation

Any design where recognition and value-extraction are separate lists needs a
detector on **both** halves. Specifically: when a notice matches DETECTION but
produces NO extracted value, that combination is itself an observable event and
should be recorded — an `eta_extraction_miss` beside the existing
`refusal_pattern_drift[]`. Otherwise the next rewording degrades quietly instead
of surfacing.

More generally still: **an empty result that is indistinguishable from a
legitimately-empty result is not a result.** Whenever "we found nothing" and
"nothing was there" share a representation, the pair needs a discriminator — the
same rule this codebase already applies to `inbox list`'s three zeros and to the
review barrier's two predicates.

## How to apply

Add the fourth pattern for the leading phrasing, and add the miss detector. Do not
treat the pattern addition alone as the fix — that closes this instance and leaves
the shape.

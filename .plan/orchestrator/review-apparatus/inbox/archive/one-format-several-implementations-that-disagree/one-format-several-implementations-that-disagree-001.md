envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=review-apparatus
kind=finding
created=2026-09-07T14:28:16Z

## A stated CodeRabbit ETA is reported as "unknown", with no drift detector to catch it

`coderabbit.md`'s `rate_limit_eta_patterns` (registry data block, three extraction
regexes) does not match the phrasing CodeRabbit actually emits on its **free-OSS**
refusal notice, so `refusal_eta` comes back empty even when the notice states a
concrete reset time.

### Observed

PR #1427, HEAD `1aec595d6`, trigger `2026-09-07T14:13:07Z`. CodeRabbit edited its
summary comment in place 11 seconds later with:

```text
[!WARNING] Review limit reached
Next included review available in 21 minutes.
Limit details: You've used the included review currently available.
You've used all free OSS reviews for now. Wait for the free limit to reset to keep
reviewing this public repository.
```

`github_re_review re-review --bot-kind coderabbit` returned
`refusal_detected: true`, `refusal_class: awaitable_window`, **`refusal_eta: ""`**.

### Why the patterns miss

All three registered extraction regexes anchor on a trailing clause this notice
does not carry:

- `wait (…) before requesting another review`
- `wait (…) before requesting another review` (unit-widened variant)
- `(…) before (?:the )?(?:rate )?limit resets`

The observed phrasing is **leading** — `Next included review available in N minutes`
— and contains neither `before requesting another review` nor `before … resets`.

### Why it is a confident-signal defect, not a cosmetic one

This is the epic's own archetype: the caller reports "rate-limited, ETA unknown"
with no indication that an ETA *was stated and was not read*. Three properties make
it silent:

1. **The refusal matched cleanly.** `Review limit reached` is in `refusal_patterns`,
   so detection succeeded and no `refusal_pattern_drift[]` record fires. The drift
   detector guards the DETECTION list; nothing guards the EXTRACTION list.
2. **An empty `eta` is indistinguishable from a notice that stated none.**
   `coderabbit.md` § "Rate-limit class" documents the empty value as the legitimate
   no-ETA case — "reports it as unknown rather than as 'reopens now'" — so the
   failure mode is spelled as intended behaviour.
3. **It is load-bearing.** `review_rate_window_await` Branch 2 derives
   `--window-seconds` from this field, so the recovery it exists to power falls back
   to a default window instead of the stated one.

### Operational cost measured on this run

Three consecutive operator waits of ~1h45m each (rounds 5, 6, 7 at 10:39:59Z,
12:25:47Z, 14:13:07Z) all refused. The stated ETA was **21 minutes**. Had it been
surfaced, each round could have retried inside its own window rather than an
arbitrary 90-minute floor — roughly five hours of unattended wall-clock spent
waiting on a signal the bot had already published.

### Second observation, weaker and offered as-is

The notice reads `You've used all free OSS reviews for now` while the plan is
reported as Team. If the free-OSS pool is shared across the org rather than being a
clean per-PR rolling hour, then *waiting longer* is the wrong remedy shape
regardless of the ETA — the productive move is retrying AT the reset, because
another repository's PR can consume the slot in between. Not established here; it
would need a cross-PR observation to confirm, and it is recorded so the next
investigator does not have to re-derive the hypothesis from scratch.

### Suggested direction (not a prescription)

Register the leading-clause phrasing as a fourth extraction pattern. The deeper
fix is that the extraction list has no drift detector at all: a refusal that
matches DETECTION but yields no ETA is currently unobservable, and that asymmetry
is what let this sit. Consider recording an `eta_extraction_miss` alongside the
existing `refusal_pattern_drift[]` when a matched refusal produces an empty `eta`,
so the next rewording surfaces instead of degrading quietly.

### Provenance

Surfaced during PLAN-TRUTH-125 finalize (`one-format-several-implementations-that-disagree`),
review rounds 5-7 against PR #1427. Not fixed in that plan — its scope is the TOON
inter-script contract, and this belongs to the review apparatus.

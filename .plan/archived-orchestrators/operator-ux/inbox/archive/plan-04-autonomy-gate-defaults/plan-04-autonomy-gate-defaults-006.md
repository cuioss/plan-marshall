envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:35:34Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=plan-04-autonomy-gate-defaults

# CodeRabbit rate_limit_eta_patterns miss the observed reset wording

## Context

At `06:53:30Z` the participation guard recorded:

> "bot_states=cuioss-review-bot:participated_but_empty,coderabbit:refused_awaitable,
> sourcery:refused_hard; ... sourcery eta='6 hours and 15 minutes'; **coderabbit
> stated no eta**; review_rate_window_await=false so no rate-window recovery was
> armed"

Sourcery's ETA extracted cleanly. CodeRabbit's did not — `eta` came back empty.
But the notice **did** state a reset time. At `08:35:31Z` the same run read it
back off the comment by eye:

> "its notice stated reset in 57 minutes (~07:23Z) and it is now 08:35Z, so the
> window has elapsed but no fresh review or fresh refusal was posted"

So the information was present in the comment and the extraction missed it.

## Root cause

`automatic-review/standards/coderabbit.md:75-78` declares all three patterns:

```
rate_limit_eta_patterns:
  - "wait ([0-9]+ minutes? and [0-9]+ seconds?) before requesting another review"
  - "wait ([0-9]+ (?:minutes?|seconds?|hours?)) before requesting another review"
  - "([0-9]+ (?:minutes?|hours?)) before (?:the )?(?:rate )?limit resets"
```

Every one requires either the trailing phrase "before requesting another review"
or "before ... limit resets". The observed notice phrases the same fact the other
way round — an availability statement ("next included review available in N
minutes") rather than a wait-instruction — so no pattern anchors.

Detection was unaffected: the refusal was correctly recognised as
`refused_awaitable` via the registry / structural arms. Only the *extraction* of
the stated window missed.

## Why this is now worse than it was during the run

During the run the miss was inert: `review_rate_window_await` was `false`, so no
recovery was armed and no consumer read `eta`.

That is no longer true. PR #1433 ("fix(automatic-review): arm the CodeRabbit
rate-window recovery") landed at `2026-09-07 10:19:47Z` — about three hours after
these refusals — and flipped `.plan/marshal.json`
`plan.phase-6-finalize.steps['plan-marshall:automatic-review'].review_rate_window_await`
from `false` to `true`.

The armed recovery is exactly the consumer of this field: on
`action: await_window` it claims the bot's rate window and polls the claim's
expiry as a bounded paced wait, capped by `review_rate_window_timeout_seconds`
(default `3600`, documented as "defaulting to 3600 to match CodeRabbit's ~hourly
rate-window reset"). With `eta` empty, the recovery runs on that generic default
instead of the window the bot itself stated. The recovery will still function —
it loses precision, not correctness — but it discards the one precise input the
bot offered, on the single bot the default was calibrated for.

## Proposed action

1. Add an availability-form pattern to `coderabbit.md`'s
   `rate_limit_eta_patterns`, anchored on the reset noun rather than the
   wait-instruction phrasing — something covering
   "available in ([0-9]+ (?:minutes?|hours?))" alongside the existing three.
2. Capture the verbatim observed body into the registry doc's prose as the
   observation the new pattern is derived from, per the standard that a
   registered bot's OBSERVED refusal text belongs in that bot's registry as a
   data record.
3. Consider making an unmatched `eta` on an `awaitable_window` refusal an
   explicit reported state rather than an indistinguishable empty string — the
   run's own two log lines show the difference between "the bot stated none" and
   "the bot stated one and we did not read it" mattered, and the guard could not
   express it.

## Evidence

- work.log `06:53:30Z` — "coderabbit stated no eta" beside a successful sourcery
  extraction, from the same call.
- work.log `08:35:31Z` — the run reading the stated 57-minute reset off the same
  comment by eye.
- `automatic-review/standards/coderabbit.md:75-78` — all three patterns require
  the wait-instruction or limit-resets phrasing.
- `git diff 29a3dad1c^ 29a3dad1c -- .plan/marshal.json` —
  `review_rate_window_await: false → true`, landed `2026-09-07 10:19:47Z`.

## Evidence limit

The verbatim CodeRabbit comment body was **not** re-read for this finding: the CI
abstraction returns `auth_failed` from the retrospective's envelope, so PR #1437
is unreachable. The wording is taken from the plan's own contemporaneous work-log
record, not from the comment. The pattern-side half — that none of the three
declared regexes can match an availability-form phrasing — is verified directly
against the registry file and does not depend on the exact observed string.

## Related, and deliberately not filed separately

The operator-side quota-wait policy ("wait 90 min, up to 10 times") did not fit
this failure: by the second iteration the window had already reopened and the
real blocker was a missing trigger event, not a closed window. The run diagnosed
that correctly after wait 1 of 10 and did not burn the budget. The machinery half
is already fixed — the armed recovery's Branch 4 is `generate_trigger`, which is
the instrument the situation needed. What survives from that observation is only
the ETA accuracy the now-armed recovery depends on, which is this finding.

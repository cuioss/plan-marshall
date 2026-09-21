envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:51:48Z

component=plan-marshall:automatic-review
category=anti-pattern

# A required bot with no re-trigger path cannot be waited out — diagnose why the retry cannot work before retrying

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-01
(`pre-commit-gate-truthfulness`, merged as PR #713 / `29d9f6c5`).

## Observation

A required review bot that (a) does not auto-review on push and (b) runs under
`re_review_on_loopback: false` has **no re-trigger path at all**. Nothing in the
loop-back cycle causes it to look at the PR again.

A wait-and-retry loop against such a bot reproduces the identical outcome forever.
Each iteration costs a full await budget (`re_review_await_timeout_seconds`, 600 s in
that run) and yields the same unproven verdict, because the retry re-asks a question
that was never re-sent.

That repository's `marshal.json` carries exactly this configuration —
`plan.phase-6-finalize.steps["plan-marshall:automatic-review"].re_review_on_loopback
= false` — verified present at relay time.

## The generalisable rule

When a gate returns the same result on every retry, the productive question is not
"how long should I wait" but:

> **What event is supposed to change this result, and does that event actually fire on
> my retry path?**

If no event fires, waiting longer is not a weaker version of the fix — it is not a fix
at any duration. The remedy is to ENABLE the re-trigger, not to extend the budget.

## Suggested remedy

`automatic-review` should detect the structural dead end and say so rather than
looping: a required bot that neither auto-reviews on push nor has
`re_review_on_loopback` enabled has no re-trigger path, and detecting that condition
should surface an actionable message naming the configuration change ("enable
`re_review_on_loopback` for {bot}, or make it optional") instead of entering an await
loop whose outcome is predetermined.

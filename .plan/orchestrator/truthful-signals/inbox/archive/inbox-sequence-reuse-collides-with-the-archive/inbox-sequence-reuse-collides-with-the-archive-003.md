envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T14:41:45Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# A rate-limit refusal is counted as a satisfied bot, producing a false clean completeness verdict

On PR #1034, `plan-marshall:automatic-review` reported sourcery as
`no_check_name` and its D3 completeness guard returned `complete: true` — a clean
review-coverage verdict.

The evidence contradicts it. `ci pr comments --pr-number 1034` shows sourcery-ai
posted an explicit **refusal**:

> you have reached your weekly rate limit of 500000 diff characters

Sourcery did not review the diff at all. A *detected* refusal was folded into a
clean-coverage verdict, so finalize reported full review coverage on a PR that
one configured reviewer never looked at.

## Why the guard is wrong

The completeness guard treats "the bot produced a review body" (or "the bot has
no check name to wait on") as participation. A rate-limit / quota / refusal body
IS a review body by shape, but it is **non-participation** by content — the bot
declined to review. Classifying it as satisfied inverts the signal the guard
exists to produce.

## Corrective action

The completeness guard must classify a rate-limit / quota-exhausted / refusal
review body as **NON-participation**, not as a satisfied bot. Concretely:

- Detect the refusal shape in the fetched review body before the completeness
  roll-up, and mark that reviewer `refused` rather than `complete`.
- A `refused` reviewer must NOT contribute to a `complete: true` verdict — it
  must surface as a coverage gap (the existing rate-window await / escalation
  path is the natural consumer).
- `no_check_name` must not be read as "nothing to wait for, therefore satisfied";
  absence of a check is unknown coverage, not confirmed coverage.

## Recurrence context

This is a **recurrence of a known archetype, not a first sighting**: the same
"enabled-bot-vs-operative drift / detected refusal reported as a clean review"
shape has been observed before (most recently #1026, where a detected refusal was
likewise reported as a clean review). Treat it as reinforcement of an existing
rule, and never read a green finalize as proof the bots saw the diff — only
`ci pr comments --pr-number N` is evidence of participation.

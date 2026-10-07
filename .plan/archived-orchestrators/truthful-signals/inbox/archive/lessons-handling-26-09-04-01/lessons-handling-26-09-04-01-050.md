envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-10T17:28:32Z

component=plan-marshall:automatic-review
category=improvement

Relayed from Token-Sheriff PLAN-09 (PR #731 / `b6b1a94d`). ⚠ Cost-shaped: a blanket wait discards an ETA the rate-limit window itself publishes.

component=plan-marshall:automatic-review
category=improvement
bundle=plan-marshall

# A review-bot rate-limit window states its own ETA; wait that, not a blanket 90-minute sleep

Repeated `@coderabbitai full review` triggers consume CodeRabbit's Fair Usage
included-review budget. This run hit four short rate-limit windows in sequence,
and each refusal named its own ETA: 57 seconds, 6 minutes, 5 minutes, 3 minutes.

The wait rule reached for was the blanket ">= 90 minute sleep" calibrated for a
real quota exhaustion window. Applied to a 57-second Fair-Usage backoff it is
wrong by roughly two orders of magnitude, and applied four times in a row it
converts about 15 minutes of stated waiting into potentially six hours of
wall-clock. There is no correctness benefit — the bot is ready when its ETA says
it is.

## Solution

Treat the two window classes as different things:

- **Fair Usage / included-review backoff** — the refusal text names a concrete
  ETA. Parse that ETA and wait exactly it (plus a small margin). These are
  typically seconds to single-digit minutes.
- **Real quota-window exhaustion** — no short ETA is offered; the long blanket
  wait is the right instrument here, and only here.

Read the stated ETA before selecting a wait. A wait rule that ignores an ETA the
provider volunteered is discarding the best signal available.

Note for the orchestrator: `plan-marshall:manage-locks` holds the cross-plan
review-bot rate-window claim, so whichever surface ends up owning the wait
duration should reconcile with that claim's window rather than sleeping
independently of it.

## Impact

Every orchestrated run that triggers a review bot more than once. The cost is
pure wall-clock and, in a bounded-timeout dispatch, an avoidable timeout.

envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T21:05:00Z

component=plan-marshall:automatic-review
category=anti-pattern
bundle=plan-marshall

# A review bot's stated rate-limit ETA is a lower bound, never a wait budget

## Observation

On PR #1041 (PLAN-92, `one-coherent-automated-review-contract`), CodeRabbit — a bot listed in
`required_bots` — posted a rate-limit refusal stating "next review available in 51 minutes".
It was still refusing roughly 30 minutes PAST that stated ETA. The vendor's rate limit is
ADAPTIVE: under sustained volume the window stretches beyond the number the refusal comment
advertises. The advertised ETA is the vendor's optimistic estimate at the moment of refusal,
not a commitment.

This matters because the same plan's D4 deliverable builds recovery directly on that number:
`review_timeout` recovery sleeps the parsed ETA, then rebase-and-pushes to generate a
new-commits event, with the registry trigger comment as a post-window fallback. The design is
correct in shape — recovery is event generation, not waiting — but the *sufficiency* of the
parsed window is a vendor-controlled variable the design currently treats as authoritative.

## Do this instead

- Treat a parsed rate-limit ETA as a **lower bound on when a retry may first be attempted**, not
  as the point at which the bot is known to be available. Never derive "the bot must have
  reviewed by now" from ETA elapsed.
- After the window elapses and the recovery event is generated, **re-check participation with the
  evidence-based detector** (D6: the bot's actual publish shape) before concluding anything. An
  elapsed window plus a pushed event is not evidence of a review.
- Keep the attempt cap. A stretched adaptive window means N retries can all land inside a single
  still-active limit; the cap is what prevents burning attempts against a window that has not
  actually opened.
- When the cap is exhausted with a required bot still refusing, that is a **reported coverage
  gap requiring an explicit operator decision**, not a condition to wait out further.

## Why it is a lesson, not a bug

The contract shipped in PLAN-92 already reports the gap truthfully — `automatic-review` recorded
"coderabbit rate-limited" and the review-retrospective recorded "1/3 bots reviewed". Nothing
laundered the gap. The lesson is about the *interpretation* of the ETA in the recovery path and
in any future prose that says "wait the stated window and the bot will review".

## Recurrence context

Instance of the epic theme (`truthful-signals`, confident-signal-hides-a-caveat): a precise,
confident-sounding number ("51 minutes") that is not the guarantee it reads as.

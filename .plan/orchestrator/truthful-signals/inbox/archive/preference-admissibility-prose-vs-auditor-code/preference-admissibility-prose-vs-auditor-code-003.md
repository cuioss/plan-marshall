envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:10:36Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# CodeRabbit's registered ETA patterns match none of its actual reset phrasing, and the doc blames the bot for the empty result

## Rule

An extraction-pattern registry whose misses are reported as "the source stated nothing" must be
re-grounded against the live source wording. Otherwise every drift in the source's phrasing is
laundered into a confident, wrong statement about the source.

## Observation

`automatic-review/standards/coderabbit.md` declares three `rate_limit_eta_patterns` (lines 64-67):

    - "wait ([0-9]+ minutes? and [0-9]+ seconds?) before requesting another review"
    - "wait ([0-9]+ (?:minutes?|seconds?|hours?)) before requesting another review"
    - "([0-9]+ (?:minutes?|hours?)) before (?:the )?(?:rate )?limit resets"

All three require either `before requesting another review` or `before ... limit resets`.
CodeRabbit's observed phrasing is **"Next included review available in N minutes"**, which matches
none of them. The pipeline therefore reports `eta: ""` for a notice that plainly states its reset.

**The doc asserts the wrong cause for that empty value.** The same file states: *"A notice that
states no ETA simply yields an empty `eta`, which the caller reports as unknown rather than as
'reopens now'."* The notice DID state its ETA. The empty value means "no registered pattern
matched", not "no ETA was stated" — and the prose collapses the two, so the operator reading it
concludes the bot was silent when in fact the registry was deaf. This is the epic's
confident-signal-hides-a-caveat shape sitting in the caveat's own explanation.

Cost in PLAN `preference-admissibility-prose-vs-auditor-code`: roughly **three hours** waiting on a
window that had already reopened.

## Second, independent finding: waiting was never the remedy

The recovery path re-triggers with `@coderabbitai review`. CodeRabbit **declines that command**,
replying that it is *"applicable only when automatic reviews are paused"*. The action that actually
produced a fresh review was **pushing a new commit**. So for this refusal shape the registered
`awaitable_window` recovery (claim window, poll to expiry, re-trigger) can burn its full
`review_rate_window_timeout_seconds` (default 3600) and still not obtain a review.

## How to apply

- Add the observed phrasing to `rate_limit_eta_patterns`, e.g.
  `"[Nn]ext included review available in ([0-9]+ (?:minutes?|hours?))"`.
- Distinguish the two empty-`eta` causes in both the payload and the prose: **no ETA stated** vs
  **stated but unmatched by any registered pattern**. A single empty string for both is the same
  zero-versus-missing collapse this project's contracts reject elsewhere.
- Re-check the sibling registries (`sourcery.md`, `cuioss-review-bot.md`) — the same
  pattern-versus-live-wording drift is untested for them too.
- Record in the recovery contract that a satisfied window does not guarantee a re-triggerable
  review; a new commit may be the only event that produces one.

## Routing note for the orchestrator

This is PR/review-apparatus surface. It was emitted here because the plan's finalize step routes
every candidate to its governing epic (`truthful-signals`) without classifying. Per the three-way
routing rule, `review-apparatus` is likely its correct home.
